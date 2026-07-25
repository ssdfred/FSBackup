from pathlib import Path

from pydantic import SecretStr

from app.modules.backup_orchestrator.schemas import (
    BackupRunRequest,
    BackupSourceMode,
)
from app.modules.backup_orchestrator.service import BackupOrchestratorService
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


def test_run_reports_planning_failure(tmp_path: Path) -> None:
    report = BackupOrchestratorService.run(
        BackupRunRequest(
            source_root=str(tmp_path / "absent"),
            destination_directory=str(tmp_path / "archives"),
            archive_name="backup",
        )
    )

    assert report.success is False
    assert report.archive_path is None
    assert report.error
