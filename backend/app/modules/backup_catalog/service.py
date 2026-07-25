import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from app.modules.encryption_engine.integration import (
    EncryptedArchiveError,
    resolved_archive_path,
)
from app.modules.integrity_engine.schemas import IntegrityRequest
from app.modules.integrity_engine.service import IntegrityEngineService

from .schemas import (
    BackupArchiveEntry,
    BackupArchiveStatus,
    BackupCatalogReport,
    BackupCatalogRequest,
    BackupCatalogSummary,
)


class BackupCatalogService:
    @staticmethod
    def scan(request: BackupCatalogRequest) -> BackupCatalogReport:
        directory = Path(request.directory).resolve()
        if not directory.is_dir():
            return BackupCatalogReport(
                directory=str(directory),
                summary=BackupCatalogSummary(
                    total=0,
                    valid=0,
                    invalid=0,
                    password_required=0,
                    encrypted=0,
                    total_size_bytes=0,
                ),
                warnings=["Backup catalog directory does not exist."],
            )

        pattern = "**/*" if request.recursive else "*"
        candidates = sorted(
            (
                path
                for path in directory.glob(pattern)
                if path.is_file() and path.suffix.casefold() in {".fsb", ".fsbe"}
            ),
            key=lambda path: str(path).casefold(),
        )
        archives = [BackupCatalogService._inspect(path, request) for path in candidates]
        return BackupCatalogReport(
            directory=str(directory),
            archives=archives,
            summary=BackupCatalogService._summary(archives),
        )

    @staticmethod
    def _inspect(path: Path, request: BackupCatalogRequest) -> BackupArchiveEntry:
        stat = path.stat()
        encrypted = path.suffix.casefold() == ".fsbe" or BackupCatalogService._is_encrypted(path)
        base = {
            "path": str(path),
            "name": path.name,
            "encrypted": encrypted,
            "size_bytes": stat.st_size,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC),
        }
        if encrypted and request.password is None:
            return BackupArchiveEntry(
                **base,
                status=BackupArchiveStatus.PASSWORD_REQUIRED,
                error="Password is required to inspect encrypted archive.",
            )

        integrity = IntegrityEngineService.verify(
            IntegrityRequest(archive_path=str(path), password=request.password)
        )
        if not integrity.valid:
            error = "; ".join(integrity.errors) or "Archive integrity verification failed."
            return BackupArchiveEntry(
                **base,
                status=BackupArchiveStatus.INVALID,
                error=error,
            )

        try:
            with resolved_archive_path(path, request.password) as resolved_path:
                with ZipFile(resolved_path, mode="r") as archive:
                    metadata = json.loads(archive.read("metadata.json"))
                    manifest = json.loads(archive.read("manifest.json"))
            summary = manifest.get("summary", {})
            return BackupArchiveEntry(
                **base,
                status=BackupArchiveStatus.VALID,
                created_at=metadata.get("created_at"),
                application_version=metadata.get("application_version"),
                file_count=len(manifest.get("files", [])),
                original_size_bytes=summary.get("estimated_size_bytes"),
            )
        except (BadZipFile, EncryptedArchiveError, OSError, ValueError, json.JSONDecodeError) as exc:
            return BackupArchiveEntry(
                **base,
                status=BackupArchiveStatus.INVALID,
                error=str(exc),
            )

    @staticmethod
    def _is_encrypted(path: Path) -> bool:
        try:
            with path.open("rb") as stream:
                return stream.read(4) == b"FSBE"
        except OSError:
            return False

    @staticmethod
    def _summary(archives: list[BackupArchiveEntry]) -> BackupCatalogSummary:
        return BackupCatalogSummary(
            total=len(archives),
            valid=sum(item.status == BackupArchiveStatus.VALID for item in archives),
            invalid=sum(item.status == BackupArchiveStatus.INVALID for item in archives),
            password_required=sum(
                item.status == BackupArchiveStatus.PASSWORD_REQUIRED for item in archives
            ),
            encrypted=sum(item.encrypted for item in archives),
            total_size_bytes=sum(item.size_bytes for item in archives),
        )
