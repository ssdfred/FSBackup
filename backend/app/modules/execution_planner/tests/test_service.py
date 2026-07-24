from pathlib import Path

import pytest

from app.modules.backup_planner.schemas import (
    BackupApplication,
    BackupItem,
    BackupPlan,
    BackupPlanSummary,
    BackupPriority,
    BackupProfile,
    BackupUser,
)
from app.modules.execution_planner.resolver import (
    DependencyResolver,
    FileDependency,
)
from app.modules.execution_planner.service import (
    ExecutionPlannerError,
    ExecutionPlannerService,
)
from app.modules.source_discovery.schemas import SourceType


class StubBackupPlanner:
    def __init__(self, plan: BackupPlan) -> None:
        self.plan = plan

    def build_plan(self, source_root: str | Path) -> BackupPlan:
        return self.plan


class StubResolver:
    def __init__(
        self,
        dependencies: dict[str, list[tuple[Path, FileDependency]]],
    ) -> None:
        self.dependencies = dependencies

    def resolve(
        self,
        *,
        application_key: str,
        category: str,
        profile_path: str | Path,
    ) -> list[tuple[Path, FileDependency]]:
        return self.dependencies.get(category, [])


def make_item(
    item_id: str,
    category: str,
    *,
    selected: bool = True,
    encrypted: bool = False,
) -> BackupItem:
    return BackupItem(
        id=item_id,
        category=category,
        title=category,
        selected=selected,
        priority=BackupPriority.CRITICAL,
        reason="test",
        encrypted=encrypted,
    )


def make_plan(
    root: Path,
    items: list[BackupItem],
    profile_path: Path,
) -> BackupPlan:
    return BackupPlan(
        source_root=str(root),
        source_type=SourceType.LOCAL_WINDOWS,
        windows_detected=True,
        users=[
            BackupUser(
                name="Alice",
                source_path=str(root / "Users" / "Alice"),
                applications=[
                    BackupApplication(
                        key="chrome",
                        name="Google Chrome",
                        profiles=[
                            BackupProfile(
                                name="Default",
                                source_path=str(profile_path),
                                items=items,
                            )
                        ],
                    )
                ],
            )
        ],
        summary=BackupPlanSummary(),
        warnings=[],
    )


def make_service(
    plan: BackupPlan,
    dependencies: dict[str, list[tuple[Path, FileDependency]]],
) -> ExecutionPlannerService:
    return ExecutionPlannerService(
        backup_planner_service=StubBackupPlanner(plan),
        dependency_resolver=StubResolver(dependencies),
    )


def test_build_plan_selects_default_items_and_sorts_them(tmp_path: Path) -> None:
    profile = tmp_path / "Users" / "Alice" / "Chrome" / "Default"
    profile.mkdir(parents=True)
    bookmarks = profile / "Bookmarks"
    history = profile / "History"
    bookmarks.write_text("fav", encoding="utf-8")
    history.write_text("hist", encoding="utf-8")

    plan = make_plan(
        tmp_path,
        [
            make_item("chrome.default.history", "history"),
            make_item("chrome.default.bookmarks", "bookmarks"),
            make_item("chrome.default.cookies", "cookies", selected=False),
        ],
        profile,
    )
    service = make_service(
        plan,
        {
            "bookmarks": [(bookmarks, FileDependency("Bookmarks"))],
            "history": [(history, FileDependency("History"))],
        },
    )

    result = service.build_plan(tmp_path)

    assert [item.logical_id for item in result.items] == [
        "chrome.default.bookmarks",
        "chrome.default.history",
    ]
    assert [file.relative_path for file in result.physical_files] == sorted(
        [str(bookmarks.relative_to(tmp_path)), str(history.relative_to(tmp_path))],
        key=str.casefold,
    )
    assert result.summary.logical_items == 2
    assert result.summary.physical_files == 2


def test_explicit_selection_removes_duplicates_and_rejects_unknown_ids(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    plan = make_plan(
        tmp_path,
        [make_item("chrome.default.bookmarks", "bookmarks")],
        profile,
    )
    service = make_service(plan, {"bookmarks": []})

    result = service.build_plan(
        tmp_path,
        ["chrome.default.bookmarks", "chrome.default.bookmarks"],
    )
    assert [item.logical_id for item in result.items] == [
        "chrome.default.bookmarks"
    ]

    with pytest.raises(ExecutionPlannerError, match="inconnus"):
        service.build_plan(tmp_path, ["unknown.item"])


def test_deduplicates_physical_files_and_merges_metadata(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    shared = profile / "Local State"
    shared.write_text("state", encoding="utf-8")
    plan = make_plan(
        tmp_path,
        [
            make_item("chrome.default.passwords", "passwords", encrypted=True),
            make_item("chrome.default.cookies", "cookies"),
        ],
        profile,
    )
    service = make_service(
        plan,
        {
            "passwords": [
                (
                    shared,
                    FileDependency(
                        "Local State",
                        mandatory=True,
                        potentially_locked=True,
                    ),
                )
            ],
            "cookies": [(shared, FileDependency("Local State"))],
        },
    )

    result = service.build_plan(tmp_path)

    assert len(result.physical_files) == 1
    assert result.physical_files[0].required_by == [
        "chrome.default.cookies",
        "chrome.default.passwords",
    ]
    assert result.physical_files[0].mandatory is True
    assert result.physical_files[0].potentially_locked is True
    assert result.summary.deduplicated_files == 1
    assert result.summary.encrypted_items == 1


def test_missing_optional_dependency_is_ignored(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    missing = profile / "optional.db"
    plan = make_plan(
        tmp_path,
        [make_item("chrome.default.history", "history")],
        profile,
    )
    service = make_service(
        plan,
        {"history": [(missing, FileDependency("optional.db"))]},
    )

    result = service.build_plan(tmp_path)

    assert result.physical_files == []
    assert result.items[0].files == []
    assert result.warnings == []


def test_missing_mandatory_dependency_is_reported(tmp_path: Path) -> None:
    profile = tmp_path / "profile"
    profile.mkdir()
    missing = profile / "required.db"
    plan = make_plan(
        tmp_path,
        [make_item("chrome.default.history", "history")],
        profile,
    )
    service = make_service(
        plan,
        {
            "history": [
                (missing, FileDependency("required.db", mandatory=True))
            ]
        },
    )

    result = service.build_plan(tmp_path)

    assert result.summary.missing_files == 1
    assert result.summary.warnings == 1
    assert result.physical_files[0].exists is False
    assert "obligatoire absente" in result.warnings[0]


def test_dependency_outside_source_root_is_rejected(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    profile = root / "profile"
    profile.mkdir()
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    plan = make_plan(
        root,
        [make_item("chrome.default.bookmarks", "bookmarks")],
        profile,
    )
    service = make_service(
        plan,
        {"bookmarks": [(outside, FileDependency("outside.txt"))]},
    )

    result = service.build_plan(root)

    assert result.physical_files == []
    assert result.summary.warnings == 1
    assert "hors de la source" in result.warnings[0]


def test_measure_path_sums_directory_files(tmp_path: Path) -> None:
    directory = tmp_path / "data"
    directory.mkdir()
    (directory / "a.bin").write_bytes(b"123")
    nested = directory / "nested"
    nested.mkdir()
    (nested / "b.bin").write_bytes(b"12345")

    assert ExecutionPlannerService._measure_path(directory) == 8
    assert ExecutionPlannerService._measure_path(tmp_path / "missing") == 0


def test_empty_backup_plan_produces_empty_execution_plan(tmp_path: Path) -> None:
    plan = BackupPlan(
        source_root=str(tmp_path),
        source_type=SourceType.LOCAL_WINDOWS,
        windows_detected=True,
        users=[],
        summary=BackupPlanSummary(),
        warnings=[],
    )
    service = make_service(plan, {})

    result = service.build_plan(tmp_path)

    assert result.items == []
    assert result.physical_files == []
    assert result.summary.logical_items == 0
    assert result.summary.estimated_size_bytes == 0


def test_dependency_resolver_handles_chromium_and_firefox_paths(
    tmp_path: Path,
) -> None:
    chromium_profile = tmp_path / "Chrome" / "Default"
    firefox_profile = tmp_path / "Firefox" / "default-release"

    resolver = DependencyResolver()
    chromium = resolver.resolve(
        application_key="chrome",
        category="passwords",
        profile_path=chromium_profile,
    )
    firefox = resolver.resolve(
        application_key="firefox",
        category="passwords",
        profile_path=firefox_profile,
    )

    assert chromium[0][0] == chromium_profile / "Login Data"
    assert chromium[2][0] == chromium_profile.parent / "Local State"
    assert firefox[0][0] == firefox_profile / "logins.json"
    assert firefox[1][0] == firefox_profile / "key4.db"


def test_dependency_resolver_returns_empty_for_unknown_category(
    tmp_path: Path,
) -> None:
    resolver = DependencyResolver()

    assert (
        resolver.resolve(
            application_key="chrome",
            category="unknown",
            profile_path=tmp_path,
        )
        == []
    )
