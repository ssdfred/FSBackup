import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

from app.modules.restore_engine.schemas import RestoreRequest
from app.modules.restore_engine.service import RestoreEngineService


def build_archive(
    archive_path: Path,
    files: dict[str, str] | None = None,
    metadata: dict[str, object] | None = None,
) -> None:
    files = files or {"profile/Preferences": "settings"}
    metadata = metadata or {
        "format": "FSB",
        "format_version": 1,
        "application": "FSBackup",
        "application_version": "0.3.0",
    }

    with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
        archive.writestr("metadata.json", json.dumps(metadata))
        archive.writestr("manifest.json", json.dumps({"files": []}))
        archive.writestr("data/", "")
        for relative_path, content in files.items():
            archive.writestr(f"data/{relative_path}", content)


def test_restore_extracts_archive_data(tmp_path: Path) -> None:
    archive_path = tmp_path / "backup.fsb"
    destination = tmp_path / "restored"
    build_archive(archive_path)

    report = RestoreEngineService.restore(
        RestoreRequest(
            archive_path=str(archive_path),
            destination_directory=str(destination),
        )
    )

    restored_file = destination / "profile" / "Preferences"
    assert restored_file.read_text(encoding="utf-8") == "settings"
    assert report.success is True
    assert report.restored_files == 1
    assert report.skipped_files == 0


def test_restore_skips_existing_file_by_default(tmp_path: Path) -> None:
    archive_path = tmp_path / "backup.fsb"
    destination = tmp_path / "restored"
    existing_file = destination / "profile" / "Preferences"
    existing_file.parent.mkdir(parents=True)
    existing_file.write_text("local", encoding="utf-8")
    build_archive(archive_path)

    report = RestoreEngineService.restore(
        RestoreRequest(
            archive_path=str(archive_path),
            destination_directory=str(destination),
        )
    )

    assert existing_file.read_text(encoding="utf-8") == "local"
    assert report.success is True
    assert report.restored_files == 0
    assert report.skipped_files == 1


def test_restore_overwrites_existing_file_when_requested(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "backup.fsb"
    destination = tmp_path / "restored"
    existing_file = destination / "profile" / "Preferences"
    existing_file.parent.mkdir(parents=True)
    existing_file.write_text("local", encoding="utf-8")
    build_archive(archive_path)

    report = RestoreEngineService.restore(
        RestoreRequest(
            archive_path=str(archive_path),
            destination_directory=str(destination),
            overwrite=True,
        )
    )

    assert existing_file.read_text(encoding="utf-8") == "settings"
    assert report.success is True
    assert report.restored_files == 1
    assert report.skipped_files == 0


def test_restore_reports_missing_archive(tmp_path: Path) -> None:
    archive_path = tmp_path / "missing.fsb"

    report = RestoreEngineService.restore(
        RestoreRequest(
            archive_path=str(archive_path),
            destination_directory=str(tmp_path / "restored"),
        )
    )

    assert report.success is False
    assert report.restored_files == 0
    assert report.error == "Archive does not exist."


def test_restore_rejects_invalid_metadata(tmp_path: Path) -> None:
    archive_path = tmp_path / "backup.fsb"
    build_archive(
        archive_path,
        metadata={"format": "ZIP", "format_version": 1},
    )

    report = RestoreEngineService.restore(
        RestoreRequest(
            archive_path=str(archive_path),
            destination_directory=str(tmp_path / "restored"),
        )
    )

    assert report.success is False
    assert report.error == "Unsupported archive format."


def test_restore_rejects_path_traversal(tmp_path: Path) -> None:
    archive_path = tmp_path / "backup.fsb"
    build_archive(archive_path, files={"../escaped.txt": "unsafe"})

    report = RestoreEngineService.restore(
        RestoreRequest(
            archive_path=str(archive_path),
            destination_directory=str(tmp_path / "restored"),
        )
    )

    assert report.success is False
    assert report.error == "Archive contains an unsafe data path."
    assert not (tmp_path / "escaped.txt").exists()
