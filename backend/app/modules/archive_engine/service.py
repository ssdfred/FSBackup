import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from zipfile import ZIP_DEFLATED, ZipFile

from .schemas import ArchiveMetadata, ArchiveReport, ArchiveRequest


class ArchiveEngineService:
    @staticmethod
    def create(request: ArchiveRequest) -> ArchiveReport:
        started_at = perf_counter()
        source_directory = Path(request.source_directory)
        destination_directory = Path(request.destination_directory)
        archive_name = ArchiveEngineService._normalize_archive_name(
            request.archive_name
        )
        archive_path = destination_directory / archive_name

        if not source_directory.is_dir():
            return ArchiveEngineService._failure_report(
                archive_path=archive_path,
                started_at=started_at,
                error="Source directory does not exist.",
            )

        try:
            destination_directory.mkdir(parents=True, exist_ok=True)

            metadata = ArchiveEngineService._create_metadata()
            files = sorted(
                path
                for path in source_directory.rglob("*")
                if path.is_file()
            )

            with ZipFile(
                archive_path,
                mode="w",
                compression=ZIP_DEFLATED,
            ) as archive:
                ArchiveEngineService._add_metadata(
                    archive=archive,
                    metadata=metadata,
                )
                ArchiveEngineService._add_manifest(
                    archive=archive,
                    request=request,
                )
                ArchiveEngineService._add_data_directory(archive=archive)
                ArchiveEngineService._add_files(
                    archive=archive,
                    source_directory=source_directory,
                    files=files,
                )

            return ArchiveReport(
                archive_path=str(archive_path),
                file_count=len(files),
                archive_size=archive_path.stat().st_size,
                duration_ms=ArchiveEngineService._duration_ms(started_at),
                success=True,
            )

        except (OSError, ValueError) as exc:
            if archive_path.exists():
                archive_path.unlink(missing_ok=True)

            return ArchiveEngineService._failure_report(
                archive_path=archive_path,
                started_at=started_at,
                error=str(exc),
            )

    @staticmethod
    def _create_metadata() -> ArchiveMetadata:
        return ArchiveMetadata(
            created_at=datetime.now(UTC),
            platform=platform.system(),
        )

    @staticmethod
    def _add_metadata(
        archive: ZipFile,
        metadata: ArchiveMetadata,
    ) -> None:
        archive.writestr(
            "metadata.json",
            json.dumps(
                metadata.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
        )

    @staticmethod
    def _add_manifest(
        archive: ZipFile,
        request: ArchiveRequest,
    ) -> None:
        archive.writestr(
            "manifest.json",
            json.dumps(
                request.manifest.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
        )

    @staticmethod
    def _add_data_directory(archive: ZipFile) -> None:
        archive.writestr("data/", "")

    @staticmethod
    def _add_files(
        archive: ZipFile,
        source_directory: Path,
        files: list[Path],
    ) -> None:
        for file_path in files:
            relative_path = file_path.relative_to(source_directory)
            archive.write(
                file_path,
                arcname=(Path("data") / relative_path).as_posix(),
            )

    @staticmethod
    def _normalize_archive_name(archive_name: str) -> str:
        name = Path(archive_name).name
        if not name:
            raise ValueError("Archive name cannot be empty.")

        if not name.lower().endswith(".fsb"):
            name = f"{name}.fsb"

        return name

    @staticmethod
    def _failure_report(
        archive_path: Path,
        started_at: float,
        error: str,
    ) -> ArchiveReport:
        return ArchiveReport(
            archive_path=str(archive_path),
            file_count=0,
            archive_size=0,
            duration_ms=ArchiveEngineService._duration_ms(started_at),
            success=False,
            error=error,
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)
