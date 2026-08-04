from pathlib import Path
from shutil import copy2 as system_copy2

from pydantic import SecretStr

from app.modules.backup_orchestrator.schemas import (
    BackupRunRequest,
    BackupSourceMode,
)
from app.modules.backup_orchestrator.service import BackupOrchestratorService
from app.modules.backup_set.repository import BackupSetRepository
from app.modules.backup_set.schemas import BackupSegmentStatus
from app.modules.encryption_engine.schemas import EncryptionSettings
from app.modules.execution_planner.schemas import (
    ExecutionPlan,
    ExecutionPlanSummary,
    PhysicalFile,
)
from app.modules.execution_planner.service import ExecutionPlannerService


def build_plan(source: Path) -> ExecutionPlan:
    source_file = source / "documents" / "note.txt"
    return ExecutionPlan(
        source_root=str(source),
        physical_files=[
            PhysicalFile(
                source_path=str(source_file),
                relative_path="documents/note.txt",
                size_bytes=source_file.stat().st_size,
                required_by=["documents.note"],
                mandatory=True,
            )
        ],
        summary=ExecutionPlanSummary(
            logical_items=1,
            physical_files=1,
            estimated_size_bytes=source_file.stat().st_size,
        ),
    )


def test_run_creates_and_verifies_encrypted_archive(tmp_path: Path, monkeypatch) -> None:
    source = tmp_path / "source"
    source_file = source / "documents" / "note.txt"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("sauvegarde orchestrée", encoding="utf-8")
    plan = build_plan(source)
    monkeypatch.setattr(
        ExecutionPlannerService,
        "build_plan",
        lambda self, source_root, selected_item_ids=None: plan,
    )

    report = BackupOrchestratorService.run(
        BackupRunRequest(
            source_root=str(source),
            source_mode=BackupSourceMode.CUSTOM_FOLDER,
            destination_directory=str(tmp_path / "archives"),
            archive_name="poste-complet",
            encryption=EncryptionSettings(password=SecretStr("mot-de-passe")),
        )
    )

    assert report.success is True
    assert report.copied_files == 1
    assert report.integrity_report is not None
    assert report.integrity_report.valid is True
    assert report.archive_path is not None
    assert Path(report.archive_path).read_bytes().startswith(b"FSBE2")


def test_run_creates_archive_from_custom_folder(tmp_path: Path) -> None:
    source = tmp_path / "source"
    nested = source / "documents"
    nested.mkdir(parents=True)
    (nested / "note.txt").write_text("dossier personnalisé", encoding="utf-8")
    (source / "image.txt").write_text("image", encoding="utf-8")

    report = BackupOrchestratorService.run(
        BackupRunRequest(
            source_root=str(source),
            source_mode=BackupSourceMode.CUSTOM_FOLDER,
            destination_directory=str(tmp_path / "archives"),
            archive_name="dossier-test",
        )
    )

    assert report.success is True
    assert report.copied_files == 2
    assert report.archive_path is not None
    assert Path(report.archive_path).suffix == ".fsb"
    assert report.integrity_report is not None
    assert report.integrity_report.valid is True


def test_run_creates_resumable_segmented_backup_set(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name in ("a.txt", "b.txt", "c.txt"):
        (source / name).write_text(name * 2, encoding="utf-8")
    destination = tmp_path / "archives"
    request = BackupRunRequest(
        source_root=str(source),
        source_mode=BackupSourceMode.CUSTOM_FOLDER,
        destination_directory=str(destination),
        archive_name="poste-fractionne",
        segmented=True,
        segment_size_bytes=6,
    )

    report = BackupOrchestratorService.run(request)

    assert report.success is True
    assert report.total_segments == 3
    assert report.completed_segments == 3
    assert report.resumed_segments == 0
    assert len(report.archive_paths) == 3
    assert all(Path(path).is_file() for path in report.archive_paths)
    manifest = BackupSetRepository.load(destination / "poste-fractionne")
    assert manifest is not None
    assert manifest.complete is True
    assert all(
        segment.status == BackupSegmentStatus.COMPLETED
        for segment in manifest.segments
    )
    assert all(segment.sha256 for segment in manifest.segments)

    resumed = BackupOrchestratorService.run(request)

    assert resumed.success is True
    assert resumed.resumed_segments == 3
    assert resumed.completed_segments == 3
    assert resumed.archive_report is not None
    assert resumed.archive_report.file_count == 3
    assert resumed.archive_report.original_size > 0
    assert resumed.archive_report.archive_size > 0
    assert resumed.integrity_report is not None
    assert resumed.integrity_report.valid is True
    assert resumed.integrity_report.checked_file_count == 3


def test_run_resumes_after_source_device_interruption(
    tmp_path: Path,
    monkeypatch,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name in ("a.txt", "b.txt", "c.txt"):
        (source / name).write_text(name * 2, encoding="utf-8")
    request = BackupRunRequest(
        source_root=str(source),
        source_mode=BackupSourceMode.CUSTOM_FOLDER,
        destination_directory=str(tmp_path / "archives"),
        archive_name="interrompue",
        segmented=True,
        segment_size_bytes=6,
    )

    class DeviceUnavailableError(OSError):
        winerror = 433

    def interrupted_copy(source_path, destination_path):
        if Path(source_path).name == "b.txt":
            raise DeviceUnavailableError("Device unavailable")
        return system_copy2(source_path, destination_path)

    monkeypatch.setattr(
        "app.modules.copy_engine.service.copy2",
        interrupted_copy,
    )

    failed = BackupOrchestratorService.run(request)

    assert failed.success is False
    assert failed.completed_segments == 1
    assert len(failed.archive_paths) == 1
    assert "disque source est devenu indisponible" in (failed.error or "")

    monkeypatch.setattr("app.modules.copy_engine.service.copy2", system_copy2)
    resumed = BackupOrchestratorService.run(request)

    assert resumed.success is True
    assert resumed.resumed_segments == 1
    assert resumed.completed_segments == 3


def test_run_rebuilds_corrupted_segment_instead_of_resuming_it(
    tmp_path: Path,
) -> None:
    source = tmp_path / "source"
    source.mkdir()
    for name in ("a.txt", "b.txt"):
        (source / name).write_text(name * 2, encoding="utf-8")
    request = BackupRunRequest(
        source_root=str(source),
        source_mode=BackupSourceMode.CUSTOM_FOLDER,
        destination_directory=str(tmp_path / "archives"),
        archive_name="corrompue",
        segmented=True,
        segment_size_bytes=6,
    )
    initial = BackupOrchestratorService.run(request)
    assert initial.success is True
    corrupted_path = Path(initial.archive_paths[0])
    corrupted_path.write_bytes(b"corrupted")

    resumed = BackupOrchestratorService.run(request)

    assert resumed.success is True
    assert resumed.resumed_segments == 1
    assert resumed.completed_segments == 2
    assert corrupted_path.read_bytes() != b"corrupted"
