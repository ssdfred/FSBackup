import json
import platform
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter
from zipfile import ZipFile

from app.modules.compression_engine.schemas import CompressionSettings
from app.modules.compression_engine.service import CompressionEngineService
from app.modules.encryption_engine.service import EncryptionEngineService

from .schemas import ArchiveMetadata, ArchiveReport, ArchiveRequest


class ArchiveEngineService:
    @staticmethod
    def create(request: ArchiveRequest) -> ArchiveReport:
        started_at = perf_counter()
        source_directory = Path(request.source_directory)
        destination_directory = Path(request.destination_directory)
        archive_name = ArchiveEngineService._normalize_archive_name(
            request.archive_name,
            encrypted=request.encryption is not None,
        )
        archive_path = destination_directory / archive_name

        if not source_directory.is_dir():
            return ArchiveEngineService._failure_report(
                archive_path=archive_path,
                started_at=started_at,
                settings=request.compression,
                encrypted=request.encryption is not None,
                error="Source directory does not exist.",
            )

        try:
            destination_directory.mkdir(parents=True, exist_ok=True)
            with TemporaryDirectory(prefix="fsbackup-archive-") as temporary_directory:
                plain_archive_path = (
                    Path(temporary_directory) / "archive.fsb"
                    if request.encryption is not None
                    else archive_path
                )
                files, metrics = ArchiveEngineService._create_plain_archive(
                    request=request,
                    source_directory=source_directory,
                    archive_path=plain_archive_path,
                )

                if request.encryption is not None:
                    encryption_report = EncryptionEngineService.encrypt_file(
                        source_path=plain_archive_path,
                        destination_path=archive_path,
                        settings=request.encryption,
                    )
                    if not encryption_report.success:
                        raise ValueError(
                            encryption_report.error or "Archive encryption failed."
                        )

            return ArchiveReport(
                archive_path=str(archive_path),
                file_count=len(files),
                archive_size=archive_path.stat().st_size,
                original_size=metrics.original_size,
                saved_bytes=metrics.saved_bytes,
                compression_ratio=metrics.ratio,
                compression_method=metrics.method,
                compression_level=metrics.level,
                encrypted=request.encryption is not None,
                duration_ms=ArchiveEngineService._duration_ms(started_at),
                success=True,
            )
        except (OSError, ValueError) as exc:
            archive_path.unlink(missing_ok=True)
            return ArchiveEngineService._failure_report(
                archive_path=archive_path,
                started_at=started_at,
                settings=request.compression,
                encrypted=request.encryption is not None,
                error=str(exc),
            )

    @staticmethod
    def _create_plain_archive(
        request: ArchiveRequest,
        source_directory: Path,
        archive_path: Path,
    ) -> tuple[list[Path], object]:
        metadata = ArchiveEngineService._create_metadata(request.compression)
        files = sorted(path for path in source_directory.rglob("*") if path.is_file())
        zip_options = CompressionEngineService.zip_options(request.compression)
        with ZipFile(
            archive_path,
            mode="w",
            strict_timestamps=False,
            **zip_options,
        ) as archive:
            ArchiveEngineService._add_metadata(archive, metadata)
            ArchiveEngineService._add_manifest(archive, request)
            archive.writestr("data/", "")
            for file_path in files:
                relative_path = file_path.relative_to(source_directory)
                archive.write(
                    file_path,
                    arcname=(Path("data") / relative_path).as_posix(),
                )
            original_size = sum(entry.file_size for entry in archive.infolist())
            compressed_size = sum(entry.compress_size for entry in archive.infolist())
        metrics = CompressionEngineService.build_metrics(
            settings=request.compression,
            original_size=original_size,
            compressed_size=compressed_size,
        )
        return files, metrics

    @staticmethod
    def _create_metadata(settings: CompressionSettings) -> ArchiveMetadata:
        return ArchiveMetadata(
            created_at=datetime.now(UTC),
            platform=platform.system(),
            compression_method=settings.method,
            compression_level=settings.level,
        )

    @staticmethod
    def _add_metadata(archive: ZipFile, metadata: ArchiveMetadata) -> None:
        archive.writestr(
            "metadata.json",
            json.dumps(metadata.model_dump(mode="json"), ensure_ascii=False, indent=2),
        )

    @staticmethod
    def _add_manifest(archive: ZipFile, request: ArchiveRequest) -> None:
        archive.writestr(
            "manifest.json",
            json.dumps(request.manifest.model_dump(mode="json"), ensure_ascii=False, indent=2),
        )

    @staticmethod
    def _normalize_archive_name(archive_name: str, encrypted: bool = False) -> str:
        name = Path(archive_name).name
        if not name:
            raise ValueError("Archive name cannot be empty.")
        suffix = ".fsbe" if encrypted else ".fsb"
        if not name.lower().endswith(suffix):
            name = f"{Path(name).stem}{suffix}"
        return name

    @staticmethod
    def _failure_report(
        archive_path: Path,
        started_at: float,
        settings: CompressionSettings,
        error: str,
        encrypted: bool = False,
    ) -> ArchiveReport:
        return ArchiveReport(
            archive_path=str(archive_path),
            file_count=0,
            archive_size=0,
            compression_method=settings.method,
            compression_level=settings.level,
            encrypted=encrypted,
            duration_ms=ArchiveEngineService._duration_ms(started_at),
            success=False,
            error=error,
        )

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return round((perf_counter() - started_at) * 1000)
