from pathlib import Path

from app.modules.copy_engine.schemas import CopyRequest, CopyStatus
from app.modules.copy_engine.service import CopyEngineService
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)


def build_single_file_plan(source: Path, relative_path: str) -> ExecutionPlan:
    return ExecutionPlan(
        source_root=str(source.parents[len(Path(relative_path).parts) - 1]),
        physical_files=[
            PhysicalFile(
                source_path=str(source),
                relative_path=relative_path,
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


def execute(plan: ExecutionPlan, destination: Path):
    return CopyEngineService.execute(
        CopyRequest(
            execution_plan=plan,
            destination_root=str(destination),
        )
    )


def test_locked_cache_file_is_reported_as_warning(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "AppData" / "Local" / "AMD" / "DxcCache" / "cache.parc"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"cache")
    plan = build_single_file_plan(
        source,
        "AppData/Local/AMD/DxcCache/cache.parc",
    )

    def deny_copy(_source, _destination):
        raise PermissionError(13, "Permission denied", str(source))

    monkeypatch.setattr("app.modules.copy_engine.service.copy2", deny_copy)

    report = execute(plan, tmp_path / "destination")

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
    plan = build_single_file_plan(source, "Documents/important.txt")

    def deny_copy(_source, _destination):
        raise PermissionError(13, "Permission denied", str(source))

    monkeypatch.setattr("app.modules.copy_engine.service.copy2", deny_copy)

    report = execute(plan, tmp_path / "destination")

    assert report.success is False
    assert report.summary.errors == 1
    assert report.files[0].status == CopyStatus.ERROR
    assert report.warnings == []
    assert len(report.errors) == 1


def test_unavailable_onedrive_placeholder_is_warning(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "Users" / "fred" / "OneDrive" / "Documents" / "cloud.docx"
    source.parent.mkdir(parents=True)
    source.write_text("placeholder", encoding="utf-8")
    plan = build_single_file_plan(
        source,
        "Users/fred/OneDrive/Documents/cloud.docx",
    )

    class CloudProviderUnavailable(OSError):
        winerror = 362

    def deny_copy(_source, _destination):
        raise CloudProviderUnavailable("Cloud provider is not running")

    monkeypatch.setattr("app.modules.copy_engine.service.copy2", deny_copy)

    report = execute(plan, tmp_path / "destination")

    assert report.success is True
    assert report.summary.missing == 1
    assert report.summary.errors == 0
    assert report.files[0].status == CopyStatus.MISSING
    assert "OneDrive" in (report.files[0].error or "")
    assert len(report.warnings) == 1
    assert report.errors == []


def test_cloud_error_outside_onedrive_remains_fatal(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "Documents" / "local.docx"
    source.parent.mkdir(parents=True)
    source.write_text("local", encoding="utf-8")
    plan = build_single_file_plan(source, "Documents/local.docx")

    class CloudProviderUnavailable(OSError):
        winerror = 362

    def deny_copy(_source, _destination):
        raise CloudProviderUnavailable("Cloud provider is not running")

    monkeypatch.setattr("app.modules.copy_engine.service.copy2", deny_copy)

    report = execute(plan, tmp_path / "destination")

    assert report.success is False
    assert report.summary.errors == 1
    assert report.files[0].status == CopyStatus.ERROR
    assert report.warnings == []
    assert len(report.errors) == 1
