from pathlib import Path

from app.modules.copy_engine.schemas import (
    CopyRequest,
    CopyStatus,
)
from app.modules.copy_engine.service import CopyEngineService
from app.modules.manifest_builder.schemas import (
    Manifest,
    ManifestFile,
    ManifestSummary,
)


def build_manifest(
    source_root: Path,
    relative_paths: list[str],
) -> Manifest:
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


def test_execute_copies_file(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"

    source_file = source_root / "profile" / "Preferences"
    source_file.parent.mkdir(parents=True)
    source_file.write_text("settings", encoding="utf-8")

    manifest = build_manifest(
        source_root=source_root,
        relative_paths=["profile/Preferences"],
    )

    report = CopyEngineService.execute(
        CopyRequest(
            manifest=manifest,
            destination_root=str(destination_root),
        )
    )

    copied_file = destination_root / "profile" / "Preferences"

    assert copied_file.read_text(encoding="utf-8") == "settings"
    assert report.summary.total_files == 1
    assert report.summary.copied == 1
    assert report.summary.errors == 0
    assert report.files[0].status == CopyStatus.COPIED


def test_execute_reports_missing_file(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"

    manifest = build_manifest(
        source_root=source_root,
        relative_paths=["missing.txt"],
    )

    report = CopyEngineService.execute(
        CopyRequest(
            manifest=manifest,
            destination_root=str(destination_root),
        )
    )

    assert report.summary.total_files == 1
    assert report.summary.missing == 1
    assert report.summary.copied == 0
    assert report.files[0].status == CopyStatus.MISSING


def test_execute_skips_existing_file_with_same_size(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"

    source_file = source_root / "data.txt"
    destination_file = destination_root / "data.txt"

    source_root.mkdir()
    destination_root.mkdir()

    source_file.write_text("same", encoding="utf-8")
    destination_file.write_text("same", encoding="utf-8")

    manifest = build_manifest(
        source_root=source_root,
        relative_paths=["data.txt"],
    )

    report = CopyEngineService.execute(
        CopyRequest(
            manifest=manifest,
            destination_root=str(destination_root),
        )
    )

    assert report.summary.skipped == 1
    assert report.summary.copied == 0
    assert report.files[0].status == CopyStatus.SKIPPED


def test_execute_continues_after_missing_file(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    destination_root = tmp_path / "destination"

    existing_file = source_root / "existing.txt"
    source_root.mkdir()
    existing_file.write_text("content", encoding="utf-8")

    manifest = build_manifest(
        source_root=source_root,
        relative_paths=[
            "missing.txt",
            "existing.txt",
        ],
    )

    report = CopyEngineService.execute(
        CopyRequest(
            manifest=manifest,
            destination_root=str(destination_root),
        )
    )

    assert report.summary.total_files == 2
    assert report.summary.missing == 1
    assert report.summary.copied == 1
    assert (
        destination_root / "existing.txt"
    ).read_text(encoding="utf-8") == "content"