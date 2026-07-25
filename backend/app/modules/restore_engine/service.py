import json
from pathlib import Path, PurePosixPath
from shutil import copyfileobj
from time import perf_counter
from zipfile import BadZipFile, ZipFile, is_zipfile

from app.modules.encryption_engine.integration import (
    EncryptedArchiveError,
    resolved_archive_path,
)

from .schemas import RestoreReport, RestoreRequest


class RestoreEngineService:
    @staticmethod
    def restore(request: RestoreRequest) -> RestoreReport:
        started_at = perf_counter()
        archive_path = Path(request.archive_path)
        destination_directory = Path(request.destination_directory)

        if not archive_path.is_file():
            return RestoreEngineService._failure_report(
                archive_path,
                destination_directory,
                started_at,
                "Archive does not exist.",
            )

        restored_files = 0
        skipped_files = 0
        try:
            with resolved_archive_path(archive_path, request.password) as resolved_path:
                if not is_zipfile(resolved_path):
                    raise ValueError("Archive is not a valid FSB file.")
                with ZipFile(resolved_path, mode="r") as archive:
                    RestoreEngineService._validate_archive(archive)
                    destination_directory.mkdir(parents=True, exist_ok=True)
                    for member in archive.infolist():
                        relative_path = RestoreEngineService._data_relative_path(
                            member.filename
                        )
                        if relative_path is None or member.is_dir():
                            continue
                        destination = destination_directory / relative_path
                        RestoreEngineService._ensure_safe_destination(
                            destination_directory,
                            destination,
                        )
                        if destination.exists() and not request.overwrite:
                            skipped_files += 1
                            continue
                        destination.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(member, mode="r") as source_stream:
                            with destination.open(mode="wb") as destination_stream:
                                copyfileobj(source_stream, destination_stream)
                        restored_files += 1
            return RestoreReport(
                archive_path=str(archive_path),
                destination_directory=str(destination_directory),
                restored_files=restored_files,
                skipped_files=skipped_files,
                duration_ms=RestoreEngineService._duration_ms(started_at),
                success=True,
            )
        except (
            BadZipFile,
            EncryptedArchiveError,
            OSError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            return RestoreEngineService._failure_report(
                archive_path,
                destination_directory,
                started_at,
                str(exc),
                restored_files,
                skipped_files,
            )

    @staticmethod
    def _validate_archive(archive: ZipFile) -> None:
        members = set(archive.namelist())
        missing_members = {"metadata.json", "manifest.json", "data/"} - members
        if missing_members:
            missing = ", ".join(sorted(missing_members))
            raise ValueError(f"Archive is missing required members: {missing}.")
        metadata = json.loads(archive.read("metadata.json"))
        if metadata.get("format") != "FSB":
            raise ValueError("Unsupported archive format.")
        if metadata.get("format_version") != 1:
            raise ValueError("Unsupported archive format version.")
        if not isinstance(json.loads(archive.read("manifest.json")), dict):
            raise ValueError("Manifest must be a JSON object.")

    @staticmethod
    def _data_relative_path(member_name: str) -> Path | None:
        pure_path = PurePosixPath(member_name)
        if not pure_path.parts or pure_path.parts[0] != "data":
            return None
        relative_parts = pure_path.parts[1:]
        if not relative_parts:
            return None
        if any(part in {"", ".", ".."} for part in relative_parts):
            raise ValueError("Archive contains an unsafe data path.")
        return Path(*relative_parts)

    @staticmethod
    def _ensure_safe_destination(
        destination_directory: Path,
        destination: Path,
    ) -> None:
        root = destination_directory.resolve()
        if not destination.resolve().is_relative_to(root):
            raise ValueError("Archive entry escapes the destination directory.")

    @staticmethod
    def _failure_report(
        archive_path: Path,
        destination_directory: Path,
        started_at: float,
        error: str,
        restored_files: int = 0,
        skipped_files: int = 0,
    ) -> RestoreReport:
        return RestoreReport(
            archive_path=str(archive_path),
            destination_directory=str(destination_directory),
            restored_files=restored_files,
            skipped_files=skipped_files,
            duration_ms=RestoreEngineService._duration_ms(started_at),
            success=False,
            error=error,
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)
