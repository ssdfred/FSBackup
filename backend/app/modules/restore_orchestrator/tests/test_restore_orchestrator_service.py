from pathlib import Path

from pydantic import SecretStr

from app.modules.archive_engine.schemas import ArchiveRequest
from app.modules.archive_engine.service import ArchiveEngineService
from app.modules.backup_orchestrator.schemas import BackupRunRequest, BackupSourceMode
from app.modules.backup_orchestrator.service import BackupOrchestratorService
from app.modules.encryption_engine.schemas import EncryptionSettings
from app.modules.manifest_builder.schemas import Manifest, ManifestFile, ManifestSummary
from app.modules.restore_orchestrator.schemas import RestoreRunRequest
from app.modules.restore_orchestrator.service import RestoreOrchestratorService


def build_archive(tmp_path: Path, encrypted: bool = False) -> tuple[Path, SecretStr | None]:
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "document.txt"
    source_file.write_text("contenu restauré", encoding="utf-8")
    password = SecretStr("mot-de-passe") if encrypted else None
    manifest = Manifest(
        created_at="2026-07-25T12:00:00Z",
        source_root=str(source),
        summary=ManifestSummary(
            logical_items=1,
            physical_files=1,
            missing_files=0,
            encrypted_items=0,
            deduplicated_files=0,
            estimated_size_bytes=source_file.stat().st_size,
            warnings=0,
        ),
        files=[
            ManifestFile(
                relative_path="document.txt",
                size=source_file.stat().st_size,
                mandatory=True,
                potentially_locked=False,
                required_by=["documents.document"],
            )
        ],
    )
    report = ArchiveEngineService.create(
        ArchiveRequest(
            source_directory=str(source),
            destination_directory=str(tmp_path / "archives"),
            archive_name="backup",
            manifest=manifest,
            encryption=(
                EncryptionSettings(password=password) if password is not None else None
            ),
        )
    )
    assert report.success is True
    return Path(report.archive_path), password


def test_run_verifies_and_restores_encrypted_archive(tmp_path: Path) -> None:
    archive_path, password = build_archive(tmp_path, encrypted=True)
    destination = tmp_path / "restored"

    report = RestoreOrchestratorService.run(
        RestoreRunRequest(
            archive_path=str(archive_path),
            destination_directory=str(destination),
            password=password,
        )
    )

    assert report.success is True
    assert report.integrity_report.valid is True
    assert report.restore_report is not None
    assert report.restore_report.restored_files == 1
    assert (destination / "document.txt").read_text(encoding="utf-8") == "contenu restauré"


def test_run_blocks_restore_when_integrity_fails(tmp_path: Path) -> None:
    archive_path, _ = build_archive(tmp_path)
    archive_path.write_bytes(archive_path.read_bytes()[:-10])
    destination = tmp_path / "restored"

    report = RestoreOrchestratorService.run(
        RestoreRunRequest(
            archive_path=str(archive_path),
            destination_directory=str(destination),
        )
    )

    assert report.success is False
    assert report.integrity_report.valid is False
    assert report.restore_report is None
    assert report.error == "Archive integrity verification failed."
    assert destination.exists() is False


def test_run_restores_complete_backup_set(tmp_path: Path) -> None:
    source = tmp_path / "set-source"
    source.mkdir()
    (source / "a.txt").write_text("alpha", encoding="utf-8")
    (source / "b.txt").write_text("bravo", encoding="utf-8")
    backup = BackupOrchestratorService.run(
        BackupRunRequest(
            source_root=str(source),
            source_mode=BackupSourceMode.CUSTOM_FOLDER,
            destination_directory=str(tmp_path / "archives"),
            archive_name="restore-set",
            segmented=True,
            segment_size_bytes=5,
        )
    )
    assert backup.success is True
    destination = tmp_path / "set-restored"

    report = RestoreOrchestratorService.run(
        RestoreRunRequest(
            archive_path=backup.backup_set_path or "",
            destination_directory=str(destination),
        )
    )

    assert report.success is True
    assert report.total_segments == 2
    assert report.restored_segments == 2
    assert report.integrity_report.valid is True
    assert report.restore_report is not None
    assert report.restore_report.restored_files == 2
    assert (destination / "a.txt").read_text(encoding="utf-8") == "alpha"
    assert (destination / "b.txt").read_text(encoding="utf-8") == "bravo"


def test_run_rejects_incomplete_backup_set(tmp_path: Path) -> None:
    backup_set = tmp_path / "incomplete"
    backup_set.mkdir()
    (backup_set / "backup-set.json").write_text(
        """{
          "backup_set_id": "test-set",
          "archive_name": "incomplete",
          "source_root": "D:\\\\",
          "created_at": "2026-08-04T18:00:00Z",
          "updated_at": "2026-08-04T18:00:00Z",
          "segment_size_bytes": 1024,
          "complete": false,
          "segments": []
        }""",
        encoding="utf-8",
    )

    report = RestoreOrchestratorService.run(
        RestoreRunRequest(
            archive_path=str(backup_set),
            destination_directory=str(tmp_path / "restored"),
        )
    )

    assert report.success is False
    assert report.restore_report is None
    assert "incomplete" in (report.error or "").casefold()
