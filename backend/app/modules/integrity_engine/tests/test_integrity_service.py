import json
from datetime import UTC, datetime
from zipfile import ZIP_DEFLATED, ZipFile

from app.modules.integrity_engine.schemas import IntegrityRequest
from app.modules.integrity_engine.service import IntegrityEngineService


def _metadata() -> dict:
    return {
        "format": "FSB",
        "format_version": 1,
        "application": "FSBackup",
        "application_version": "0.3.0",
        "created_at": datetime.now(UTC).isoformat(),
        "platform": "Windows",
    }


def _manifest(size: int = 5) -> dict:
    return {
        "format_version": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "source_root": "C:/source",
        "summary": {
            "logical_items": 1,
            "physical_files": 1,
            "missing_files": 0,
            "encrypted_items": 0,
            "deduplicated_files": 0,
            "estimated_size_bytes": size,
            "warnings": 0,
        },
        "files": [
            {
                "relative_path": "docs/file.txt",
                "size": size,
                "mandatory": True,
                "potentially_locked": False,
                "required_by": [],
            }
        ],
    }


def _create_archive(path, *, metadata=None, manifest=None, data=b"hello"):
    with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
        if metadata is not False:
            archive.writestr("metadata.json", json.dumps(metadata or _metadata()))
        if manifest is not False:
            archive.writestr("manifest.json", json.dumps(manifest or _manifest()))
        archive.writestr("data/", "")
        if data is not None:
            archive.writestr("data/docs/file.txt", data)


def test_valid_archive(tmp_path):
    archive_path = tmp_path / "backup.fsb"
    _create_archive(archive_path)

    report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=str(archive_path))
    )

    assert report.valid is True
    assert report.checked_file_count == 1
    assert report.errors == []


def test_missing_archive(tmp_path):
    report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=str(tmp_path / "missing.fsb"))
    )

    assert report.valid is False
    assert "Archive file does not exist." in report.errors


def test_invalid_zip(tmp_path):
    archive_path = tmp_path / "invalid.fsb"
    archive_path.write_text("not a zip", encoding="utf-8")

    report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=str(archive_path))
    )

    assert report.valid is False
    assert "Archive is not a valid ZIP/FSB file." in report.errors


def test_missing_required_entry(tmp_path):
    archive_path = tmp_path / "missing-metadata.fsb"
    _create_archive(archive_path, metadata=False)

    report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=str(archive_path))
    )

    assert report.valid is False
    assert any("metadata.json" in error for error in report.errors)


def test_invalid_metadata(tmp_path):
    archive_path = tmp_path / "invalid-metadata.fsb"
    _create_archive(archive_path, metadata={"format": "OTHER"})

    report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=str(archive_path))
    )

    assert report.valid is False
    assert any("Invalid metadata.json" in error for error in report.errors)


def test_missing_manifest_file(tmp_path):
    archive_path = tmp_path / "missing-file.fsb"
    _create_archive(archive_path, data=None)

    report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=str(archive_path))
    )

    assert report.valid is False
    assert report.missing_files == ["data/docs/file.txt"]


def test_size_mismatch(tmp_path):
    archive_path = tmp_path / "size-mismatch.fsb"
    _create_archive(archive_path, data=b"different")

    report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=str(archive_path))
    )

    assert report.valid is False
    assert report.size_mismatches == ["data/docs/file.txt"]


def test_unexpected_file_is_warning(tmp_path):
    archive_path = tmp_path / "unexpected.fsb"
    _create_archive(archive_path)
    with ZipFile(archive_path, "a", compression=ZIP_DEFLATED) as archive:
        archive.writestr("data/extra.txt", "extra")

    report = IntegrityEngineService.verify(
        IntegrityRequest(archive_path=str(archive_path))
    )

    assert report.valid is True
    assert report.unexpected_files == ["data/extra.txt"]
    assert report.warnings
