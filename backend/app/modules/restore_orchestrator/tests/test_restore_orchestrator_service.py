from pathlib import Path

from pydantic import SecretStr

from app.modules.archive_engine.schemas import ArchiveRequest
from app.modules.archive_engine.service import ArchiveEngineService
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
            estimated_size_bytes=source_file.stat().st_size,
        ),
        files=[
            ManifestFile(
                relative_path="document.txt",
                size=source_file.stat().st_size,
                mandatory=True,
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
