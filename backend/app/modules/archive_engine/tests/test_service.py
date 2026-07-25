import json
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from app.modules.archive_engine.schemas import ArchiveRequest
from app.modules.archive_engine.service import ArchiveEngineService
from app.modules.compression_engine.schemas import (
    CompressionMethod,
    CompressionSettings,
)
from app.modules.manifest_builder.schemas import (
    Manifest,
    ManifestFile,
    ManifestSummary,
)


def build_manifest(source_root: Path, relative_paths: list[str]) -> Manifest:
    files = [
        ManifestFile(
            relative_path=relative_path,
            size=0,
            mandatory=True,
            potentially_locked=False,
            required_by=["test.item"],
        )
        for relative_path in relative_paths
    ]

    return Manifest(
        created_at="2026-07-24T08:00:00Z",
        source_root=str(source_root),
        summary=ManifestSummary(
            logical_items=1,
            physical_files=len(files),
            missing_files=0,
            encrypted_items=0,
            deduplicated_files=0,
            estimated_size_bytes=0,
            warnings=0,
        ),
        files=files,
    )


def test_create_builds_readable_archive(tmp_path: Path) -> None:
    source_directory = tmp_path / "copied"
    destination_directory = tmp_path / "archives"
    source_file = source_directory / "Chrome" / "Preferences"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("settings", encoding="utf-8")

    manifest = build_manifest(
        source_root=source_directory,
        relative_paths=["Chrome/Preferences"],
    )

    report = ArchiveEngineService.create(
        ArchiveRequest(
            source_directory=str(source_directory),
            destination_directory=str(destination_directory),
            archive_name="backup.fsb",
            manifest=manifest,
        )
    )

    archive_path = Path(report.archive_path)

    assert report.success is True
    assert report.error is None
    assert report.file_count == 1
    assert report.archive_size > 0
    assert report.original_size > 0
    assert report.compression_method == CompressionMethod.DEFLATED
    assert report.compression_level == 6
    assert archive_path.is_file()

    with ZipFile(archive_path) as archive:
        names = archive.namelist()
        assert "metadata.json" in names
        assert "manifest.json" in names
        assert "data/" in names
        assert "data/Chrome/Preferences" in names
        assert archive.read("data/Chrome/Preferences") == b"settings"
        assert archive.getinfo("data/Chrome/Preferences").compress_type == ZIP_DEFLATED


def test_create_embeds_metadata_and_manifest(tmp_path: Path) -> None:
    source_directory = tmp_path / "copied"
    destination_directory = tmp_path / "archives"
    source_directory.mkdir()

    manifest = build_manifest(
        source_root=source_directory,
        relative_paths=[],
    )

    report = ArchiveEngineService.create(
        ArchiveRequest(
            source_directory=str(source_directory),
            destination_directory=str(destination_directory),
            archive_name="backup",
            manifest=manifest,
        )
    )

    assert report.success is True
    assert report.archive_path.endswith("backup.fsb")

    with ZipFile(report.archive_path) as archive:
        metadata = json.loads(archive.read("metadata.json"))
        archived_manifest = json.loads(archive.read("manifest.json"))

    assert metadata["format"] == "FSB"
    assert metadata["format_version"] == 1
    assert metadata["application"] == "FSBackup"
    assert metadata["application_version"] == "0.6.0"
    assert metadata["created_at"]
    assert metadata["platform"]
    assert metadata["compression_method"] == "deflated"
    assert metadata["compression_level"] == 6
    assert archived_manifest == manifest.model_dump(mode="json")


def test_create_supports_stored_archives(tmp_path: Path) -> None:
    source_directory = tmp_path / "copied"
    destination_directory = tmp_path / "archives"
    source_directory.mkdir()
    (source_directory / "data.txt").write_text("content", encoding="utf-8")

    report = ArchiveEngineService.create(
        ArchiveRequest(
            source_directory=str(source_directory),
            destination_directory=str(destination_directory),
            archive_name="stored.fsb",
            manifest=build_manifest(source_directory, ["data.txt"]),
            compression=CompressionSettings(
                method=CompressionMethod.STORED,
                level=0,
            ),
        )
    )

    assert report.success is True
    assert report.compression_method == CompressionMethod.STORED
    assert report.compression_level == 0
    assert report.saved_bytes == 0
    assert report.compression_ratio == 1.0

    with ZipFile(report.archive_path) as archive:
        assert all(entry.compress_type == ZIP_STORED for entry in archive.infolist())


def test_deflated_archive_reduces_repetitive_payload(tmp_path: Path) -> None:
    source_directory = tmp_path / "copied"
    destination_directory = tmp_path / "archives"
    source_directory.mkdir()
    (source_directory / "large.txt").write_text("FSBackup" * 5000, encoding="utf-8")

    report = ArchiveEngineService.create(
        ArchiveRequest(
            source_directory=str(source_directory),
            destination_directory=str(destination_directory),
            archive_name="compressed.fsb",
            manifest=build_manifest(source_directory, ["large.txt"]),
            compression=CompressionSettings(level=9),
        )
    )

    assert report.success is True
    assert report.compression_level == 9
    assert report.saved_bytes > 0
    assert 0 < report.compression_ratio < 1


def test_create_reports_missing_source_directory(tmp_path: Path) -> None:
    source_directory = tmp_path / "missing"
    destination_directory = tmp_path / "archives"
    manifest = build_manifest(
        source_root=source_directory,
        relative_paths=[],
    )

    report = ArchiveEngineService.create(
        ArchiveRequest(
            source_directory=str(source_directory),
            destination_directory=str(destination_directory),
            archive_name="backup.fsb",
            manifest=manifest,
        )
    )

    assert report.success is False
    assert report.file_count == 0
    assert report.archive_size == 0
    assert report.original_size == 0
    assert report.error == "Source directory does not exist."
    assert not Path(report.archive_path).exists()
