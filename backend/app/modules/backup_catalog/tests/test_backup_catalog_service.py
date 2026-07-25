from pathlib import Path

from pydantic import SecretStr

from app.modules.archive_engine.schemas import ArchiveRequest
from app.modules.archive_engine.service import ArchiveEngineService
from app.modules.backup_catalog.schemas import BackupCatalogRequest
from app.modules.backup_catalog.service import BackupCatalogService
from app.modules.encryption_engine.schemas import EncryptionSettings
from app.modules.manifest_builder.schemas import Manifest, ManifestFile, ManifestSummary


def create_archive(
    tmp_path: Path,
    name: str,
    password: SecretStr | None = None,
) -> Path:
    source = tmp_path / f"source-{name}"
    source.mkdir()
    source_file = source / "document.txt"
    source_file.write_text(f"contenu {name}", encoding="utf-8")
    manifest = Manifest(
        created_at="2026-07-25T12:00:00Z",
        source_root=str(source),
        summary=ManifestSummary(
            logical_items=1,
            physical_files=1,
            missing_files=0,
            encrypted_items=1 if password is not None else 0,
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
            archive_name=name,
            manifest=manifest,
            encryption=(
                EncryptionSettings(password=password) if password is not None else None
            ),
        )
    )
    assert report.success is True
    return Path(report.archive_path)


def test_catalog_lists_valid_and_invalid_archives(tmp_path: Path) -> None:
    archives = tmp_path / "archives"
    valid_path = create_archive(tmp_path, "valid")
    invalid_path = archives / "broken.fsb"
    invalid_path.write_bytes(b"not-an-archive")

    report = BackupCatalogService.scan(
        BackupCatalogRequest(directory=str(archives))
    )

    assert report.summary.total == 2
    assert report.summary.valid == 1
    assert report.summary.invalid == 1
    valid = next(item for item in report.archives if item.path == str(valid_path))
    assert valid.file_count == 1
    assert valid.original_size_bytes == len("contenu valid".encode())


def test_catalog_requires_password_then_inspects_encrypted_archive(tmp_path: Path) -> None:
    password = SecretStr("mot-de-passe")
    archive_path = create_archive(tmp_path, "encrypted", password)
    archives = archive_path.parent

    protected = BackupCatalogService.scan(
        BackupCatalogRequest(directory=str(archives))
    )
    unlocked = BackupCatalogService.scan(
        BackupCatalogRequest(directory=str(archives), password=password)
    )

    assert protected.summary.password_required == 1
    assert protected.archives[0].encrypted is True
    assert unlocked.summary.valid == 1
    assert unlocked.archives[0].file_count == 1
