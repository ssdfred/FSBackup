from pathlib import Path

from pydantic import SecretStr

from app.modules.archive_engine.schemas import ArchiveRequest
from app.modules.archive_engine.service import ArchiveEngineService
from app.modules.encryption_engine.schemas import EncryptionSettings
from app.modules.integrity_engine.schemas import IntegrityRequest
from app.modules.integrity_engine.service import IntegrityEngineService
from app.modules.manifest_builder.schemas import Manifest, ManifestFile, ManifestSummary
from app.modules.restore_engine.schemas import RestoreRequest
from app.modules.restore_engine.service import RestoreEngineService


def build_manifest(source_root: Path, relative_path: str, size: int) -> Manifest:
    return Manifest(
        created_at="2026-07-25T08:00:00Z",
        source_root=str(source_root),
        summary=ManifestSummary(
            logical_items=1,
            physical_files=1,
            missing_files=0,
            encrypted_items=0,
            deduplicated_files=0,
            estimated_size_bytes=size,
            warnings=0,
        ),
        files=[
            ManifestFile(
                relative_path=relative_path,
                size=size,
                mandatory=True,
                potentially_locked=False,
                required_by=["test.item"],
            )
        ],
    )


def test_encrypted_archive_complete_workflow(tmp_path: Path) -> None:
    source = tmp_path / "source"
    destination = tmp_path / "archives"
    restored = tmp_path / "restored"
    source.mkdir()
    source_file = source / "document.txt"
    source_file.write_text("contenu protégé", encoding="utf-8")
    password = SecretStr("mot-de-passe-test")

    archive_report = ArchiveEngineService.create(
        ArchiveRequest(
            source_directory=str(source),
            destination_directory=str(destination),
            archive_name="backup",
            manifest=build_manifest(
                source,
                "document.txt",
                source_file.stat().st_size,
            ),
            encryption=EncryptionSettings(password=password),
        )
    )

    assert archive_report.success is True
    assert archive_report.encrypted is True
    assert archive_report.archive_path.endswith(".fsbe")
    assert Path(archive_report.archive_path).read_bytes().startswith(b"FSBE1")

    integrity_report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=archive_report.archive_path, password=password)
    )
    assert integrity_report.valid is True

    restore_report = RestoreEngineService.restore(
        RestoreRequest(
            archive_path=archive_report.archive_path,
            destination_directory=str(restored),
            password=password,
        )
    )
    assert restore_report.success is True
    assert (restored / "document.txt").read_text(encoding="utf-8") == "contenu protégé"


def test_encrypted_archive_requires_valid_password(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    source_file = source / "document.txt"
    source_file.write_text("secret", encoding="utf-8")
    report = ArchiveEngineService.create(
        ArchiveRequest(
            source_directory=str(source),
            destination_directory=str(tmp_path / "archives"),
            archive_name="backup",
            manifest=build_manifest(source, "document.txt", source_file.stat().st_size),
            encryption=EncryptionSettings(password=SecretStr("correct")),
        )
    )

    missing_password = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=report.archive_path)
    )
    wrong_password = RestoreEngineService.restore(
        RestoreRequest(
            archive_path=report.archive_path,
            destination_directory=str(tmp_path / "restored"),
            password=SecretStr("incorrect"),
        )
    )

    assert missing_password.valid is False
    assert missing_password.errors == ["Password is required for encrypted archive."]
    assert wrong_password.success is False
    assert wrong_password.error == "Invalid password or encrypted file integrity check failed."
