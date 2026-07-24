"""Tests for the intelligent backup planner service."""

from __future__ import annotations

from pathlib import Path

from app.modules.backup_planner.schemas import BackupPriority, BackupUser
from app.modules.backup_planner.service import (
    BackupPlannerService,
    LogicalItemDefinition,
)
from app.modules.source_discovery.schemas import (
    DataAvailability,
    DiscoveredBrowser,
    DiscoveredBrowserProfile,
    DiscoveredUser,
    SourceDiscoveryReport,
    SourceType,
)


class StubDiscoveryService:
    """Return a predefined discovery report."""

    def __init__(self, report: SourceDiscoveryReport) -> None:
        self.report = report
        self.received_source: str | Path | None = None

    def discover(self, source_root: str | Path) -> SourceDiscoveryReport:
        self.received_source = source_root
        return self.report


def _profile(
    path: Path,
    *,
    name: str = "Default",
    bookmarks: bool = False,
    passwords: bool = False,
    cookies: bool = False,
    history: bool = False,
    potentially_encrypted: list[str] | None = None,
) -> DiscoveredBrowserProfile:
    return DiscoveredBrowserProfile(
        name=name,
        path=str(path),
        data=DataAvailability(
            bookmarks=bookmarks,
            passwords=passwords,
            cookies=cookies,
            history=history,
            potentially_encrypted=potentially_encrypted or [],
        ),
    )


def _report(
    browser: DiscoveredBrowser,
    *,
    warnings: list[str] | None = None,
) -> SourceDiscoveryReport:
    return SourceDiscoveryReport(
        source_root="E:\\",
        source_type=SourceType.WINDOWS_DISK,
        windows_detected=True,
        users_directory="E:\\Users",
        users=[
            DiscoveredUser(
                name="Fred",
                path="E:\\Users\\Fred",
                browsers=[browser],
            )
        ],
        warnings=warnings or [],
    )


def test_build_plan_transforms_discovery_report(tmp_path: Path) -> None:
    profile_path = tmp_path / "Default"
    profile_path.mkdir()
    (profile_path / "Bookmarks").write_bytes(b"1234")

    browser = DiscoveredBrowser(
        key="chrome",
        name="Google Chrome",
        profile_root=str(profile_path.parent),
        profiles=[_profile(profile_path, bookmarks=True)],
    )
    discovery = StubDiscoveryService(_report(browser, warnings=["warning"]))

    plan = BackupPlannerService(discovery).build_plan("E:\\")

    assert discovery.received_source == "E:\\"
    assert plan.source_root == "E:\\"
    assert plan.source_type is SourceType.WINDOWS_DISK
    assert plan.windows_detected is True
    assert plan.warnings == ["warning"]
    assert plan.users[0].name == "Fred"
    assert plan.users[0].applications[0].key == "chrome"
    assert plan.users[0].applications[0].profiles[0].items[0].category == "bookmarks"
    assert plan.summary.users == 1
    assert plan.summary.applications == 1
    assert plan.summary.profiles == 1
    assert plan.summary.selected_items == 1
    assert plan.summary.estimated_size_bytes == 4
    assert plan.summary.estimated_files == 1


def test_browser_without_profiles_is_not_added_to_plan() -> None:
    browser = DiscoveredBrowser(
        key="chrome",
        name="Google Chrome",
        profile_root="E:\\Users\\Fred\\Chrome",
        profiles=[],
    )

    plan = BackupPlannerService(StubDiscoveryService(_report(browser))).build_plan(
        "E:\\"
    )

    assert plan.users[0].applications == []
    assert plan.summary.applications == 0
    assert plan.summary.profiles == 0
    assert plan.summary.items == 0


def test_chromium_items_include_selected_and_excluded_categories(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "Profile 1"
    cache_path = profile_path / "Cache"
    cache_path.mkdir(parents=True)
    (profile_path / "History").write_bytes(b"history")
    (cache_path / "entry.bin").write_bytes(b"cache")

    browser = DiscoveredBrowser(
        key="edge",
        name="Microsoft Edge",
        profile_root=str(profile_path.parent),
        profiles=[_profile(profile_path, name="Profile 1", history=True)],
    )

    plan = BackupPlannerService(StubDiscoveryService(_report(browser))).build_plan(
        tmp_path
    )
    items = plan.users[0].applications[0].profiles[0].items
    by_category = {item.category: item for item in items}

    assert by_category["history"].selected is True
    assert by_category["history"].priority is BackupPriority.OPTIONAL
    assert by_category["cache"].selected is False
    assert by_category["cache"].priority is BackupPriority.IGNORE
    assert by_category["cache"].estimated_files == 1
    assert plan.summary.selected_items == 1
    assert plan.summary.excluded_items == 1
    assert plan.summary.estimated_size_bytes == len(b"history")


def test_firefox_uses_firefox_storage_paths(tmp_path: Path) -> None:
    profile_path = tmp_path / "firefox-profile"
    profile_path.mkdir()
    (profile_path / "logins.json").write_bytes(b"login")
    (profile_path / "key4.db").write_bytes(b"key")

    browser = DiscoveredBrowser(
        key="firefox",
        name="Mozilla Firefox",
        profile_root=str(profile_path.parent),
        profiles=[_profile(profile_path, passwords=True)],
    )

    plan = BackupPlannerService(StubDiscoveryService(_report(browser))).build_plan(
        tmp_path
    )
    item = plan.users[0].applications[0].profiles[0].items[0]

    assert item.category == "passwords"
    assert item.encrypted is True
    assert item.estimated_files == 2
    assert item.estimated_size_bytes == 8


def test_potentially_encrypted_category_is_marked_encrypted(
    tmp_path: Path,
) -> None:
    profile_path = tmp_path / "Default"
    profile_path.mkdir()
    (profile_path / "Bookmarks").write_text("bookmark", encoding="utf-8")

    browser = DiscoveredBrowser(
        key="chrome",
        name="Google Chrome",
        profile_root=str(profile_path.parent),
        profiles=[
            _profile(
                profile_path,
                bookmarks=True,
                potentially_encrypted=["bookmarks"],
            )
        ],
    )

    plan = BackupPlannerService(StubDiscoveryService(_report(browser))).build_plan(
        tmp_path
    )

    assert plan.users[0].applications[0].profiles[0].items[0].encrypted is True
    assert plan.summary.encrypted_items == 1


def test_create_item_generates_stable_normalized_identifier() -> None:
    definition = LogicalItemDefinition(
        category="bookmarks",
        title="Favoris",
        priority=BackupPriority.CRITICAL,
        selected=True,
        reason="Important",
    )

    item = BackupPlannerService._create_item(
        browser_key="chrome",
        profile_name=" Profile. 1 ",
        definition=definition,
        estimated_size_bytes=10,
        estimated_files=2,
        encrypted=False,
    )

    assert item.id == "chrome.profile--1.bookmarks"
    assert item.estimated_size_bytes == 10
    assert item.estimated_files == 2


def test_estimate_item_does_not_count_same_file_twice(tmp_path: Path) -> None:
    profile_path = tmp_path / "Default"
    profile_path.mkdir()
    (profile_path / "places.sqlite").write_bytes(b"places")

    service = BackupPlannerService()

    size, count = service._estimate_item(
        profile_path=profile_path,
        browser_family="firefox",
        category="bookmarks",
    )

    assert size == len(b"places")
    assert count == 1


def test_measure_path_returns_zero_for_missing_path(tmp_path: Path) -> None:
    service = BackupPlannerService()

    assert service._measure_path(tmp_path / "missing", set()) == (0, 0)


def test_summary_counts_only_selected_size_and_files() -> None:
    users = [
        BackupUser(
            name="Fred",
            source_path="E:\\Users\\Fred",
            applications=[],
        )
    ]

    summary = BackupPlannerService._build_summary(users)

    assert summary.users == 1
    assert summary.applications == 0
    assert summary.profiles == 0
    assert summary.items == 0
    assert summary.estimated_size_bytes == 0
    assert summary.estimated_files == 0
