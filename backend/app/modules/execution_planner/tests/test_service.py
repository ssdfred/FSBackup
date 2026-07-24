"""Tests for the physical execution planner."""

from __future__ import annotations

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
    """Return a predefined logical plan."""

    def __init__(self, plan: BackupPlan) -> None:
        self.plan = plan

    def build_plan(self, source_root: str | Path) -> BackupPlan:
        return self.plan


class StaticResolver:
    """Return predefined physical dependencies."""

    def __init__(
        self,
        dependencies: list[tuple[Path, FileDependency]],
    ) -> None:
        self.dependencies = dependencies

    def resolve(self, **_: object) -> list[tuple[Path, FileDependency]]:
        return self.dependencies


def make_item(
    logical_id: str,
    category: str,
    *,
    selected: bool = True,
    encrypted: bool = False,
) -> BackupItem:
    return BackupItem(
        id=logical_id,
        category=category,
        title=category.title(),
        selected=selected,
        priority=BackupPriority.CRITICAL,
        reason="Test",
        encrypted=encrypted,
    )


def make_plan(
    root: Path,
    profile_path: Path,
    items: list[BackupItem],
    *,
    application_key: str = "chrome",
) -> BackupPlan:
    return BackupPlan(
        source_root=str(root),
        source_type=SourceType.WINDOWS_DISK,
        windows_detected=True,
        users=[
            BackupUser(
                name="Alice",
                source_path=str(root / "Users" / "Alice"),
                applications=[
                    BackupApplication(
                        key=application_key,
                        name=application_key.title(),
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
    )


def make_service(
    plan: BackupPlan,
    resolver: object | None = None,
) -> ExecutionPlannerService:
    return ExecutionPlannerService(
        backup_planner_service=StubBackupPlanner(plan),
        dependency_resolver=resolver or DependencyResolver(),
    )


def test_dependency_resolver_uses_browser_root_for_chromium_local_state(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "User Data" / "Default"

    dependencies = DependencyResolver().resolve(
        application_key="chrome",
        category="passwords",
        profile_path=profile,
    )

    paths = [path for path, _ in dependencies]
    assert profile / "Login Data" in paths
    assert profile.parent / "Local State" in paths


def test_dependency_resolver_uses_profile_root_for_firefox(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "Profiles" / "default-release"

    dependencies = DependencyResolver().resolve(
        application_key="firefox",
        category="bookmarks",
        profile_path=profile,
    )

    assert [path for path, _ in dependencies] == [
        profile / "places.sqlite",
        profile / "favicons.sqlite",
        profile / "bookmarkbackups",
    ]


def test_build_plan_selects_only_default_selected_items(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "User Data" / "Default"
    profile.mkdir(parents=True)
    (profile / "Bookmarks").write_bytes(b"abc")
    plan = make_plan(
        tmp_path,
        profile,
        [
            make_item("chrome.default.bookmarks", "bookmarks"),
            make_item(
                "chrome.default.cache",
                "cache",
                selected=False,
            ),
        ],
    )

    result = make_service(plan).build_plan(tmp_path)

    assert [item.logical_id for item in result.items] == [
        "chrome.default.bookmarks"
    ]
    assert result.summary.logical_items == 1
    assert result.summary.physical_files == 1
    assert result.summary.estimated_size_bytes == 3


def test_explicit_selection_is_deduplicated_and_sorted(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "User Data" / "Default"
    profile.mkdir(parents=True)
    (profile / "Bookmarks").write_text("bookmarks", encoding="utf-8")
    (profile / "Preferences").write_text("prefs", encoding="utf-8")
    plan = make_plan(
        tmp_path,
        profile,
        [
            make_item("chrome.default.preferences", "preferences"),
            make_item("chrome.default.bookmarks", "bookmarks"),
        ],
    )

    result = make_service(plan).build_plan(
        tmp_path,
        selected_item_ids=[
            "chrome.default.preferences",
            "chrome.default.bookmarks",
            "chrome.default.preferences",
        ],
    )

    assert [item.logical_id for item in result.items] == [
        "chrome.default.bookmarks",
        "chrome.default.preferences",
    ]


def test_unknown_selected_item_raises_clear_error(tmp_path: Path) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    plan = make_plan(tmp_path, profile, [])

    with pytest.raises(
        ExecutionPlannerError,
        match="Identifiants de sauvegarde inconnus",
    ):
        make_service(plan).build_plan(
            tmp_path,
            selected_item_ids=["unknown.item"],
        )


def test_missing_mandatory_dependency_is_preserved_with_warning(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "User Data" / "Default"
    profile.mkdir(parents=True)
    plan = make_plan(
        tmp_path,
        profile,
        [make_item("chrome.default.bookmarks", "bookmarks")],
    )

    result = make_service(plan).build_plan(tmp_path)

    assert result.summary.missing_files == 1
    assert result.summary.warnings == 1
    assert len(result.physical_files) == 1
    assert result.physical_files[0].exists is False
    assert result.physical_files[0].mandatory is True
    assert "Dépendance obligatoire absente" in result.warnings[0]


def test_missing_optional_dependency_is_ignored(tmp_path: Path) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    plan = make_plan(
        tmp_path,
        profile,
        [make_item("chrome.default.cache", "cache")],
    )

    result = make_service(plan).build_plan(
        tmp_path,
        selected_item_ids=["chrome.default.cache"],
    )

    assert result.physical_files == []
    assert result.items[0].files == []
    assert result.warnings == []


def test_shared_physical_file_is_deduplicated_between_items(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "Profiles" / "default-release"
    profile.mkdir(parents=True)
    (profile / "places.sqlite").write_bytes(b"places")
    plan = make_plan(
        tmp_path,
        profile,
        [
            make_item("firefox.default.bookmarks", "bookmarks"),
            make_item("firefox.default.history", "history"),
        ],
        application_key="firefox",
    )

    result = make_service(plan).build_plan(tmp_path)

    places = next(
        file
        for file in result.physical_files
        if file.relative_path.endswith("places.sqlite")
    )
    assert places.required_by == [
        "firefox.default.bookmarks",
        "firefox.default.history",
    ]
    assert result.summary.deduplicated_files == 1


def test_summary_counts_encrypted_items_and_unique_sizes(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    first = profile / "first.db"
    second = profile / "second.db"
    first.write_bytes(b"1234")
    second.write_bytes(b"12")
    items = [
        make_item("browser.default.passwords", "passwords", encrypted=True),
        make_item("browser.default.cookies", "cookies"),
    ]
    plan = make_plan(tmp_path, profile, items)
    resolver = StaticResolver(
        [
            (first, FileDependency("first.db", mandatory=True)),
            (second, FileDependency("second.db")),
        ]
    )

    result = make_service(plan, resolver).build_plan(tmp_path)

    assert result.summary.logical_items == 2
    assert result.summary.encrypted_items == 1
    assert result.summary.physical_files == 2
    assert result.summary.estimated_size_bytes == 6
    assert result.summary.deduplicated_files == 2


def test_dependency_outside_source_root_is_ignored(tmp_path: Path) -> None:
    root = tmp_path / "source"
    root.mkdir()
    profile = root / "Default"
    profile.mkdir()
    outside = tmp_path / "outside.db"
    outside.write_bytes(b"secret")
    plan = make_plan(
        root,
        profile,
        [make_item("browser.default.passwords", "passwords")],
    )
    resolver = StaticResolver(
        [(outside, FileDependency("outside.db", mandatory=True))]
    )

    result = make_service(plan, resolver).build_plan(root)

    assert result.physical_files == []
    assert result.summary.warnings == 1
    assert "hors de la source" in result.warnings[0]


def test_directory_dependency_size_is_measured_recursively(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "Default"
    directory = profile / "Extensions"
    nested = directory / "extension-a"
    nested.mkdir(parents=True)
    (directory / "manifest.json").write_bytes(b"123")
    (nested / "data.bin").write_bytes(b"12345")
    plan = make_plan(
        tmp_path,
        profile,
        [make_item("chrome.default.extensions", "extensions")],
    )

    result = make_service(plan).build_plan(tmp_path)

    extension_directory = next(
        file
        for file in result.physical_files
        if file.relative_path.endswith("Extensions")
    )
    assert extension_directory.size_bytes == 8
    assert result.summary.estimated_size_bytes == 8
