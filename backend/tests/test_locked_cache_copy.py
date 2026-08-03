from pathlib import Path

from app.modules.copy_engine.schemas import CopyRequest, CopyStatus
from app.modules.copy_engine.service import CopyEngineService
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)


def test_locked_cache_file_is_reported_as_warning(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "AppData" / "Local" / "AMD" / "DxcCache" / "cache.parc"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"cache")
    plan = ExecutionPlan(
        source_root=str(tmp_path),
        physical_files=[
            PhysicalFile(
                source_path=str(source),
                relative_path="AppData/Local/AMD/DxcCache/cache.parc",
                size_bytes=source.stat().st_size,
            )
        ],
        summary=ExecutionPlanSummary(
            logical_items=1,
            physical_files=1,
            estimated_size_bytes=source.stat().st_size,
        ),
    )

    def deny_copy(_source, _destination):
        raise PermissionError(13, "Permission denied", str(source))

    monkeypatch.setattr("app.modules.copy_engine.service.copy2", deny_copy)

    report = CopyEngineService.execute(
        CopyRequest(
            execution_plan=plan,
            destination_root=str(tmp_path / "destination"),
        )
    )

    assert report.success is True
    assert report.summary.missing == 1
    assert report.summary.errors == 0
    assert report.files[0].status == CopyStatus.MISSING
    assert len(report.warnings) == 1
    assert report.errors == []


def test_locked_regular_file_remains_fatal(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "Documents" / "important.txt"
    source.parent.mkdir(parents=True)
    source.write_text("important", encoding="utf-8")
    plan = ExecutionPlan(
        source_root=str(tmp_path),
        physical_files=[
            PhysicalFile(
                source_path=str(source),
                relative_path="Documents/important.txt",
                size_bytes=source.stat().st_size,
                mandatory=True,
            )
        ],
        summary=ExecutionPlanSummary(
            logical_items=1,
            physical_files=1,
            estimated_size_bytes=source.stat().st_size,
        ),
    )

    def deny_copy(_source, _destination):
        raise PermissionError(13, "Permission denied", str(source))

    monkeypatch.setattr("app.modules.copy_engine.service.copy2", deny_copy)

    report = CopyEngineService.execute(
        CopyRequest(
            execution_plan=plan,
            destination_root=str(tmp_path / "destination"),
        )
    )

    assert report.success is False
    assert report.summary.errors == 1
    assert report.files[0].status == CopyStatus.ERROR
    assert report.warnings == []
    assert len(report.errors) == 1
