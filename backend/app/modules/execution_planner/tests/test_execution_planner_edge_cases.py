"""Additional edge-case tests for the execution planner."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.modules.execution_planner.resolver import FileDependency
from app.modules.execution_planner.schemas import ExecutionItem, PhysicalFile
from app.modules.execution_planner.service import (
    ExecutionPlannerService,
    build_execution_plan,
)


class FailingPath:
    """Path-like object raising errors for selected filesystem operations."""

    def __init__(self, *, file_error: bool = False, dir_error: bool = False) -> None:
        self.file_error = file_error
        self.dir_error = dir_error

    def is_file(self) -> bool:
        if self.file_error:
            raise OSError("fichier inaccessible")
        return False

    def is_dir(self) -> bool:
        if self.dir_error:
            raise OSError("dossier inaccessible")
        return False


class BrokenRglobPath:
    """Directory-like object whose recursive listing cannot be created."""

    def is_file(self) -> bool:
        return False

    def is_dir(self) -> bool:
        return True

    def rglob(self, pattern: str) -> object:
        raise OSError(f"lecture impossible: {pattern}")


class CandidateWithFailingStat:
    """File-like recursive candidate whose metadata is unreadable."""

    def is_file(self) -> bool:
        return True

    def stat(self) -> object:
        raise OSError("métadonnées indisponibles")


class DirectoryWithCandidates:
    """Directory-like object returning predefined recursive candidates."""

    def __init__(self, candidates: list[object]) -> None:
        self.candidates = candidates

    def is_file(self) -> bool:
        return False

    def is_dir(self) -> bool:
        return True

    def rglob(self, pattern: str) -> list[object]:
        assert pattern == "*"
        return self.candidates


def test_measure_path_returns_zero_for_non_file_and_non_directory() -> None:
    """Unsupported filesystem entries must contribute no bytes."""

    assert ExecutionPlannerService._measure_path(FailingPath()) == 0  # type: ignore[arg-type]


def test_measure_path_tolerates_initial_filesystem_error() -> None:
    """An error while identifying a path must not abort planning."""

    path = FailingPath(file_error=True)

    assert ExecutionPlannerService._measure_path(path) == 0  # type: ignore[arg-type]


def test_measure_path_tolerates_recursive_listing_error() -> None:
    """An unreadable directory must be reported with a zero size."""

    assert ExecutionPlannerService._measure_path(BrokenRglobPath()) == 0  # type: ignore[arg-type]


def test_measure_path_skips_unreadable_recursive_candidates() -> None:
    """One unreadable child must not prevent measuring the directory."""

    readable = pytest.MonkeyPatch()
    try:
        file_path = Path("readable.bin")
        readable.setattr(Path, "is_file", lambda self: self == file_path)
        readable.setattr(
            Path,
            "stat",
            lambda self: type("Stat", (), {"st_size": 7})(),
        )
        directory = DirectoryWithCandidates(
            [file_path, CandidateWithFailingStat()]
        )

        assert ExecutionPlannerService._measure_path(directory) == 7  # type: ignore[arg-type]
    finally:
        readable.undo()


def test_is_inside_root_rejects_unrelated_path(tmp_path: Path) -> None:
    """The root isolation helper must reject unrelated paths."""

    root = tmp_path / "source"
    outside = tmp_path / "outside"

    assert ExecutionPlannerService._is_inside_root(root, outside) is False


def test_build_summary_ignores_missing_file_sizes() -> None:
    """Only existing files must contribute to the estimated size."""

    items = [
        ExecutionItem(
            logical_id="browser.default.passwords",
            category="passwords",
            application_key="browser",
            application_name="Browser",
            user_name="Alice",
            profile_name="Default",
            encrypted=True,
            files=[],
            warnings=[],
        )
    ]
    files = [
        PhysicalFile(
            source_path="present.db",
            relative_path="present.db",
            size_bytes=12,
            required_by=["browser.default.passwords"],
            mandatory=True,
            exists=True,
            potentially_locked=False,
            warnings=[],
        ),
        PhysicalFile(
            source_path="missing.db",
            relative_path="missing.db",
            size_bytes=99,
            required_by=["browser.default.passwords"],
            mandatory=True,
            exists=False,
            potentially_locked=False,
            warnings=["absent"],
        ),
    ]

    summary = ExecutionPlannerService._build_summary(
        execution_items=items,
        physical_files=files,
        deduplicated_files=0,
        warnings=["absent"],
    )

    assert summary.logical_items == 1
    assert summary.physical_files == 2
    assert summary.missing_files == 1
    assert summary.encrypted_items == 1
    assert summary.estimated_size_bytes == 12
    assert summary.warnings == 1


def test_build_physical_file_returns_missing_mandatory_warning(
    tmp_path: Path,
) -> None:
    """A mandatory missing path must remain represented in the plan."""

    service = ExecutionPlannerService()
    candidate = tmp_path / "missing.db"

    physical_file, warning = service._build_physical_file(
        root=tmp_path,
        candidate=candidate,
        dependency=FileDependency("missing.db", mandatory=True),
        logical_id="browser.default.passwords",
    )

    assert physical_file is not None
    assert physical_file.exists is False
    assert physical_file.size_bytes == 0
    assert warning is not None
    assert "Dépendance obligatoire absente" in warning


def test_convenience_entry_point_delegates_to_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The public helper must forward source and selected identifiers."""

    sentinel = object()
    captured: dict[str, object] = {}

    def fake_build_plan(
        self: ExecutionPlannerService,
        source_root: str | Path,
        selected_item_ids: list[str] | None = None,
    ) -> object:
        captured["source_root"] = source_root
        captured["selected_item_ids"] = selected_item_ids
        return sentinel

    monkeypatch.setattr(ExecutionPlannerService, "build_plan", fake_build_plan)

    result = build_execution_plan(tmp_path, ["browser.default.bookmarks"])

    assert result is sentinel
    assert captured == {
        "source_root": tmp_path,
        "selected_item_ids": ["browser.default.bookmarks"],
    }
