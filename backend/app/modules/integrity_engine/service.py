import json
from pathlib import Path, PurePosixPath
from time import perf_counter
from zipfile import BadZipFile, ZipFile

from pydantic import ValidationError

from app.modules.archive_engine.schemas import ArchiveMetadata
from app.modules.encryption_engine.integration import (
    EncryptedArchiveError,
    resolved_archive_path,
)
from app.modules.manifest_builder.schemas import Manifest

from .schemas import IntegrityReport, IntegrityRequest


class IntegrityEngineService:
    REQUIRED_ENTRIES = {"metadata.json", "manifest.json", "data/"}

    @staticmethod
    def verify(request: IntegrityRequest) -> IntegrityReport:
        started_at = perf_counter()
        archive_path = Path(request.archive_path)
        if not archive_path.is_file():
            return IntegrityEngineService._report(
                archive_path,
                started_at,
                errors=["Archive file does not exist."],
            )
        try:
            with resolved_archive_path(archive_path, request.password) as resolved_path:
                return IntegrityEngineService._verify_zip(
                    display_path=archive_path,
                    resolved_path=resolved_path,
                    started_at=started_at,
                )
        except EncryptedArchiveError as exc:
            return IntegrityEngineService._report(
                archive_path,
                started_at,
                errors=[str(exc)],
            )

    @staticmethod
    def _verify_zip(
        display_path: Path,
        resolved_path: Path,
        started_at: float,
    ) -> IntegrityReport:
        errors: list[str] = []
        warnings: list[str] = []
        missing_files: list[str] = []
        unexpected_files: list[str] = []
        size_mismatches: list[str] = []
        checked_file_count = 0
        try:
            with ZipFile(resolved_path, mode="r") as archive:
                entries = set(archive.namelist())
                missing_entries = sorted(IntegrityEngineService.REQUIRED_ENTRIES - entries)
                if missing_entries:
                    errors.append(
                        "Missing required archive entries: " + ", ".join(missing_entries)
                    )
                crc_failure = archive.testzip()
                if crc_failure is not None:
                    errors.append(f"CRC verification failed for: {crc_failure}")
                metadata = IntegrityEngineService._read_metadata(archive, errors)
                manifest = IntegrityEngineService._read_manifest(archive, errors)
                if metadata is not None:
                    if metadata.format != "FSB":
                        errors.append("Unsupported archive format.")
                    if metadata.format_version != 1:
                        errors.append("Unsupported archive format version.")
                if manifest is not None:
                    (
                        checked_file_count,
                        missing_files,
                        unexpected_files,
                        size_mismatches,
                    ) = IntegrityEngineService._verify_manifest_files(archive, manifest)
                    if missing_files:
                        errors.append("Files declared in manifest are missing.")
                    if size_mismatches:
                        errors.append("File sizes do not match the manifest.")
                    if unexpected_files:
                        warnings.append(
                            "Archive contains files not declared in manifest."
                        )
        except BadZipFile:
            errors.append("Archive is not a valid ZIP/FSB file.")
        except (OSError, RuntimeError) as exc:
            errors.append(str(exc))
        return IntegrityEngineService._report(
            display_path,
            started_at,
            checked_file_count,
            missing_files,
            unexpected_files,
            size_mismatches,
            errors,
            warnings,
        )

    @staticmethod
    def _read_metadata(archive: ZipFile, errors: list[str]) -> ArchiveMetadata | None:
        if "metadata.json" not in archive.namelist():
            return None
        try:
            return ArchiveMetadata.model_validate(
                json.loads(archive.read("metadata.json"))
            )
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
            errors.append(f"Invalid metadata.json: {exc}")
            return None

    @staticmethod
    def _read_manifest(archive: ZipFile, errors: list[str]) -> Manifest | None:
        if "manifest.json" not in archive.namelist():
            return None
        try:
            return Manifest.model_validate(json.loads(archive.read("manifest.json")))
        except (json.JSONDecodeError, UnicodeDecodeError, ValidationError) as exc:
            errors.append(f"Invalid manifest.json: {exc}")
            return None

    @staticmethod
    def _verify_manifest_files(
        archive: ZipFile,
        manifest: Manifest,
    ) -> tuple[int, list[str], list[str], list[str]]:
        archive_files = {
            info.filename: info.file_size
            for info in archive.infolist()
            if info.filename.startswith("data/") and not info.filename.endswith("/")
        }
        expected_files = {
            IntegrityEngineService._data_entry(file.relative_path): file.size
            for file in manifest.files
        }
        missing = sorted(set(expected_files) - set(archive_files))
        unexpected = sorted(set(archive_files) - set(expected_files))
        size_mismatches = sorted(
            name
            for name in set(expected_files) & set(archive_files)
            if expected_files[name] != archive_files[name]
        )
        return len(set(expected_files) & set(archive_files)), missing, unexpected, size_mismatches

    @staticmethod
    def _data_entry(relative_path: str) -> str:
        normalized = PurePosixPath(relative_path.replace("\\", "/"))
        return (PurePosixPath("data") / normalized).as_posix()

    @staticmethod
    def _report(
        archive_path: Path,
        started_at: float,
        checked_file_count: int = 0,
        missing_files: list[str] | None = None,
        unexpected_files: list[str] | None = None,
        size_mismatches: list[str] | None = None,
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> IntegrityReport:
        report_errors = errors or []
        return IntegrityReport(
            archive_path=str(archive_path),
            valid=not report_errors,
            checked_file_count=checked_file_count,
            missing_files=missing_files or [],
            unexpected_files=unexpected_files or [],
            size_mismatches=size_mismatches or [],
            errors=report_errors,
            warnings=warnings or [],
            duration_ms=round((perf_counter() - started_at) * 1000),
        )
