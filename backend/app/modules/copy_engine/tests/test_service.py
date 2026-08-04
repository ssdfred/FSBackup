from pathlib import Path
from uuid import UUID

from app.modules.copy_engine.schemas import CopyRequest, CopyStatus
from app.modules.copy_engine.service import CopyEngineService
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)


def build_plan(
    source_root: Path,
    relative_paths: list[str],
) -> ExecutionPlan:
    files = [
        PhysicalFile(
            source_path=str(source_root / relative_path),
            relative_path=relative_path,
            size_bytes=(source_root / relative_path).stat().st_size
            if (source_root / relative_path).is_file()
            else 0,
            required_by=["test.item"],
            mandatory=True,
            exists=(source_root / relative_path).is_file(),
        )
        for relative_path in relative_paths
    ]

    return ExecutionPlan(
        source_root=str(source_root),
        physical_files=files,
        summary=ExecutionPlanSummary(
            logical_items=1,
            physical_files=len(files),
            missing_files=sum(not file.exists for file in files),
            encrypted_items=0,
            estimated_size_bytes=sum(file.size_bytes for file in files),
            deduplicated_files=0,
            warnings=0,
        ),
    )


def execute_plan(plan: ExecutionPlan, destination_root: Path):
    return CopyEngineService.execute(
        CopyRequest(
            execution_plan=plan,
            destination_root=str(destination_root),
        )
    )


def test_execute_copies_file(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_file = source_root / "profile" / "Preferences"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("settings", encoding="utf-8")

    report = execute_plan(
        build_plan(source_root, ["profile/Preferences"]),
        destination_root,
    )

    copied_file = destination_root / "profile" / "Preferences"
    assert copied_file.read_text(encoding="utf-8") == "settings"
    assert report.summary.total_files == 1
    assert report.summary.copied == 1
    assert report.summary.errors == 0
    assert report.files[0].status == CopyStatus.COPIED
    assert report.success is True
    assert isinstance(report.execution_id, UUID)
    assert report.started_at <= report.finished_at
    assert report.duration_ms == report.summary.duration_ms
    assert report.warnings == []
    assert report.errors == []
    assert report.metadata["planned_files"] == 1


def test_execute_reports_missing_file_as_warning(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"

    report = execute_plan(
        build_plan(source_root, ["missing.txt"]),
        destination_root,
    )

    assert report.summary.total_files == 1
    assert report.summary.missing == 1
    assert report.summary.copied == 0
    assert report.files[0].status == CopyStatus.MISSING
    assert report.success is True
    assert len(report.warnings) == 1
    assert report.warnings[0].code == "source_missing"
    assert report.errors == []


def test_execute_skips_existing_file_with_same_size(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    destination_root.mkdir()
    (source_root / "data.txt").write_text("same", encoding="utf-8")
    (destination_root / "data.txt").write_text("same", encoding="utf-8")

    report = execute_plan(
        build_plan(source_root, ["data.txt"]),
        destination_root,
    )

    assert report.summary.skipped == 1
    assert report.summary.copied == 0
    assert report.files[0].status == CopyStatus.SKIPPED
    assert report.success is True


def test_execute_continues_after_missing_file(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    (source_root / "existing.txt").write_text("content", encoding="utf-8")

    report = execute_plan(
        build_plan(source_root, ["missing.txt", "existing.txt"]),
        destination_root,
    )

    assert report.summary.total_files == 2
    assert report.summary.missing == 1
    assert report.summary.copied == 1
    assert report.success is True
    assert (destination_root / "existing.txt").read_text(
        encoding="utf-8"
    ) == "content"


def test_execute_treats_file_disappearing_during_copy_as_warning(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    source_file = source_root / "volatile.tmp"
    source_file.write_text("temporary", encoding="utf-8")
    plan = build_plan(source_root, ["volatile.tmp"])

    def disappearing_copy(source, destination):
        Path(source).unlink()
        raise FileNotFoundError(3, "The system cannot find the path specified")

    monkeypatch.setattr(
        "app.modules.copy_engine.service.copy2",
        disappearing_copy,
    )

    report = execute_plan(plan, destination_root)

    assert report.success is True
    assert report.summary.missing == 1
    assert report.summary.errors == 0
    assert report.files[0].status == CopyStatus.MISSING
    assert report.warnings[0].code == "source_missing"
    assert report.errors == []


def test_execute_rejects_path_outside_destination(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    source_file = source_root / "secret.txt"
    source_file.write_text("secret", encoding="utf-8")

    plan = ExecutionPlan(
        source_root=str(source_root),
        physical_files=[
            PhysicalFile(
                source_path=str(source_file),
                relative_path="../secret.txt",
                size_bytes=source_file.stat().st_size,
            )
        ],
        summary=ExecutionPlanSummary(
            logical_items=1,
            physical_files=1,
            missing_files=0,
            encrypted_items=0,
            estimated_size_bytes=source_file.stat().st_size,
            deduplicated_files=0,
            warnings=0,
        ),
    )

    report = execute_plan(plan, destination_root)

    assert report.summary.errors == 1
    assert report.files[0].status == CopyStatus.ERROR
    assert report.success is False
    assert len(report.errors) == 1
    assert report.errors[0].code == "copy_failed"
    assert report.warnings == []
    assert not (tmp_path / "secret.txt").exists()


def test_execute_stops_when_source_device_becomes_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"
    source_root.mkdir()
    (source_root / "first.txt").write_text("first", encoding="utf-8")
    (source_root / "second.txt").write_text("second", encoding="utf-8")
    plan = build_plan(source_root, ["first.txt", "second.txt"])

    class DeviceUnavailableError(OSError):
        winerror = 433

    calls = 0

    def unavailable_copy(_source, _destination):
        nonlocal calls
        calls += 1
        raise DeviceUnavailableError("Device unavailable")

    monkeypatch.setattr(
        "app.modules.copy_engine.service.copy2",
        unavailable_copy,
    )

    report = execute_plan(plan, destination_root)

    assert calls == 1
    assert report.success is False
    assert report.summary.total_files == 1
    assert report.summary.errors == 1
    assert report.files[0].winerror == 433
    assert "disque source est devenu indisponible" in report.errors[0].message
