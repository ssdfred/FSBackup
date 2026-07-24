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
from app.modules.execution_planner.schemas import ExecutionItem, PhysicalFile
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


class CategoryResolver:
    """Return dependencies selected by logical category."""

    def __init__(
        self,
        dependencies: dict[str, list[tuple[Path, FileDependency]]],
    ) -> None:
        self.dependencies = dependencies

    def resolve(
        self,
        *,
        category: str,
        **_: object,
    ) -> list[tuple[Path, FileDependency]]:
        return self.dependencies.get(category, [])


class UnresolvablePath:
    """Path-like test double whose resolution always fails."""

    def resolve(self, *, strict: bool = False) -> Path:
        raise OSError("accès refusé")

    def __str__(self) -> str:
        return "unresolvable.db"


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


def test_dependency_resolver_returns_empty_list_for_unknown_category(
    tmp_path: Path,
) -> None:
    result = DependencyResolver().resolve(
        application_key="chrome",
        category="unknown",
        profile_path=tmp_path / "Default",
    )

    assert result == []


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


def test_empty_explicit_selection_builds_empty_plan(tmp_path: Path) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    plan = make_plan(
        tmp_path,
        profile,
        [make_item("chrome.default.bookmarks", "bookmarks")],
    )

    result = make_service(plan).build_plan(tmp_path, selected_item_ids=[])

    assert result.items == []
    assert result.physical_files == []
    assert result.warnings == []
    assert result.summary.logical_items == 0
    assert result.summary.physical_files == 0


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


def test_duplicate_file_merges_mandatory_and_locked_flags(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    shared = profile / "shared.db"
    shared.write_bytes(b"data")
    plan = make_plan(
        tmp_path,
        profile,
        [
            make_item("browser.default.first", "first"),
            make_item("browser.default.second", "second"),
        ],
    )
    resolver = CategoryResolver(
        {
            "first": [(shared, FileDependency("shared.db"))],
            "second": [
                (
                    shared,
                    FileDependency(
                        "shared.db",
                        mandatory=True,
                        potentially_locked=True,
                    ),
                )
            ],
        }
    )

    result = make_service(plan, resolver).build_plan(tmp_path)

    physical_file = result.physical_files[0]
    assert physical_file.required_by == [
        "browser.default.first",
        "browser.default.second",
    ]
    assert physical_file.mandatory is True
    assert physical_file.potentially_locked is True
    assert result.summary.deduplicated_files == 1


def test_duplicate_dependency_within_one_item_keeps_unique_file_path(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    shared = profile / "shared.db"
    shared.write_bytes(b"data")
    plan = make_plan(
        tmp_path,
        profile,
        [make_item("browser.default.first", "first")],
    )
    dependency = FileDependency("shared.db", mandatory=True)
    resolver = StaticResolver([(shared, dependency), (shared, dependency)])

    result = make_service(plan, resolver).build_plan(tmp_path)

    assert len(result.physical_files) == 1
    assert result.items[0].files == [str(shared.resolve())]
    assert result.physical_files[0].required_by == ["browser.default.first"]
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


def test_unresolvable_dependency_is_ignored_with_warning(
    tmp_path: Path,
) -> None:
    profile = tmp_path / "Default"
    profile.mkdir()
    plan = make_plan(
        tmp_path,
        profile,
        [make_item("browser.default.passwords", "passwords")],
    )
    resolver = StaticResolver(
        [
            (
                UnresolvablePath(),  # type: ignore[arg-type]
                FileDependency("unresolvable.db", mandatory=True),
            )
        ]
    )

    result = make_service(plan, resolver).build_plan(tmp_path)

    assert result.physical_files == []
    assert result.summary.warnings == 1
    assert "Impossible de résoudre le chemin" in result.warnings[0]
    assert "accès refusé" in result.warnings[0]


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


def test_measure_path_returns_zero_for_missing_path(tmp_path: Path) -> None:
    assert ExecutionPlannerService._measure_path(tmp_path / "missing") == 0


def test_is_inside_root_accepts_descendants_and_rejects_siblings(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"

    assert ExecutionPlannerService._is_inside_root(root, root / "file.db")
    assert not ExecutionPlannerService._is_inside_root(
        root,
        tmp_path / "source-copy" / "file.db",
    )


def test_build_summary_ignores_missing_file_sizes() -> None:
    execution_items = [
        ExecutionItem(
            logical_id="item.encrypted",
            category="passwords",
            application_key="chrome",
            application_name="Chrome",
            user_name="Alice",
            profile_name="Default",
            encrypted=True,
        )
    ]
    physical_files = [
        PhysicalFile(
            source_path="existing.db",
            relative_path="existing.db",
            size_bytes=10,
            exists=True,
        ),
        PhysicalFile(
            source_path="missing.db",
            relative_path="missing.db",
            size_bytes=999,
            exists=False,
            mandatory=True,
        ),
    ]

    summary = ExecutionPlannerService._build_summary(
        execution_items=execution_items,
        physical_files=physical_files,
        deduplicated_files=3,
        warnings=["warning"],
    )

    assert summary.logical_items == 1
    assert summary.physical_files == 2
    assert summary.missing_files == 1
    assert summary.encrypted_items == 1
    assert summary.estimated_size_bytes == 10
    assert summary.deduplicated_files == 3
    assert summary.warnings == 1
