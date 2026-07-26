from pathlib import Path

import pytest

from app.modules.execution_planner.windows_service import WindowsExecutionPlannerService
from app.modules.source_discovery.service import SourceDiscoveryService


def _write(path: Path, size: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"x" * size)


def _allow_temporary_root(monkeypatch: pytest.MonkeyPatch, root: Path) -> None:
    monkeypatch.setattr(
        SourceDiscoveryService,
        "_validate_source_root",
        lambda _self, _source: root.resolve(strict=True),
    )


def test_windows_plan_includes_personal_folders_and_selected_project(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "Windows").mkdir()
    (tmp_path / "ProgramData").mkdir()
    (tmp_path / "Program Files").mkdir()
    _write(tmp_path / "Users" / "fred" / "Documents" / "document.txt", 11)
    _write(tmp_path / "Users" / "fred" / "Downloads" / "archive.zip", 13)
    project = tmp_path / "laragon" / "www" / "site"
    _write(project / "index.php", 17)
    _allow_temporary_root(monkeypatch, tmp_path)

    plan = WindowsExecutionPlannerService.build_plan(
        tmp_path,
        selected_additional_paths=[str(project)],
    )

    relative_paths = {item.relative_path for item in plan.physical_files}
    assert str(Path("Users/fred/Documents/document.txt")) in relative_paths
    assert str(Path("Users/fred/Downloads/archive.zip")) in relative_paths
    assert str(Path("laragon/www/site/index.php")) in relative_paths
    assert plan.summary.estimated_size_bytes == 41


def test_windows_plan_refuses_system_folder_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "Windows").mkdir()
    (tmp_path / "ProgramData").mkdir()
    (tmp_path / "Program Files").mkdir()
    _allow_temporary_root(monkeypatch, tmp_path)

    with pytest.raises(ValueError, match="Dossier système non sélectionnable"):
        WindowsExecutionPlannerService.build_plan(
            tmp_path,
            selected_additional_paths=[str(tmp_path / "Windows")],
        )
