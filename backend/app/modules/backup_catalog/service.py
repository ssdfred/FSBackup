import json
from datetime import UTC, datetime
from pathlib import Path
from zipfile import BadZipFile, ZipFile

from app.modules.backup_set.repository import BackupSetRepository
from app.modules.backup_set.schemas import BackupSegmentStatus
from app.modules.backup_set.service import BackupSetService
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
        set_pattern = "**/backup-set.json" if request.recursive else "*/backup-set.json"
        set_manifests = sorted(
            directory.glob(set_pattern),
            key=lambda path: str(path).casefold(),
        )
        root_manifest = BackupSetRepository.manifest_path(directory)
        if root_manifest.is_file() and root_manifest not in set_manifests:
            set_manifests.insert(0, root_manifest)
        set_archives = BackupCatalogService._set_archive_paths(set_manifests)
        candidates = sorted(
            (
                path
                for path in directory.glob(pattern)
                if path.is_file() and path.suffix.casefold() in {".fsb", ".fsbe"}
                and path.resolve() not in set_archives
            ),
            key=lambda path: str(path).casefold(),
        )
        archives = [
            BackupCatalogService._inspect_set(path, request)
            for path in set_manifests
        ] + [BackupCatalogService._inspect(path, request) for path in candidates]
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
    def _set_archive_paths(manifest_paths: list[Path]) -> set[Path]:
        archive_paths: set[Path] = set()
        for manifest_path in manifest_paths:
            try:
                manifest = BackupSetRepository.load(manifest_path.parent)
            except (OSError, ValueError):
                continue
            if manifest is None:
                continue
            archive_paths.update(
                (manifest_path.parent / segment.archive_name).resolve()
                for segment in manifest.segments
            )
        return archive_paths

    @staticmethod
    def _inspect_set(
        manifest_path: Path,
        request: BackupCatalogRequest,
    ) -> BackupArchiveEntry:
        stat = manifest_path.stat()
        base = {
            "path": str(manifest_path),
            "name": manifest_path.parent.name,
            "size_bytes": 0,
            "modified_at": datetime.fromtimestamp(stat.st_mtime, tz=UTC),
            "backup_set": True,
        }
        try:
            manifest = BackupSetRepository.load(manifest_path.parent)
            if manifest is None:
                raise ValueError("Backup-set manifest is missing.")
            archive_paths = [
                manifest_path.parent / segment.archive_name
                for segment in manifest.segments
            ]
            total_size = sum(
                path.stat().st_size for path in archive_paths if path.is_file()
            )
            details = {
                **base,
                "name": manifest.archive_name,
                "encrypted": manifest.encrypted,
                "size_bytes": total_size,
                "created_at": manifest.created_at,
                "file_count": sum(segment.file_count for segment in manifest.segments),
                "original_size_bytes": sum(
                    segment.size_bytes for segment in manifest.segments
                ),
                "segment_count": len(manifest.segments),
                "completed_segments": sum(
                    segment.status == BackupSegmentStatus.COMPLETED
                    for segment in manifest.segments
                ),
            }
            if manifest.encrypted and request.password is None:
                return BackupArchiveEntry(
                    **details,
                    status=BackupArchiveStatus.PASSWORD_REQUIRED,
                    error="Password is required to inspect encrypted backup set.",
                )
            if not manifest.complete:
                return BackupArchiveEntry(
                    **details,
                    status=BackupArchiveStatus.INVALID,
                    error="Backup set is incomplete and can be resumed.",
                )
            for segment, archive_path in zip(
                manifest.segments,
                archive_paths,
                strict=True,
            ):
                if not archive_path.is_file():
                    raise ValueError(f"Backup segment is missing: {segment.name}")
                if (
                    segment.sha256 is None
                    or BackupSetService.file_sha256(archive_path) != segment.sha256
                ):
                    raise ValueError(f"Backup segment checksum failed: {segment.name}")
                integrity = IntegrityEngineService.verify(
                    IntegrityRequest(
                        archive_path=str(archive_path),
                        password=request.password,
                    )
                )
                if not integrity.valid:
                    raise ValueError(f"Backup segment integrity failed: {segment.name}")
            return BackupArchiveEntry(
                **details,
                status=BackupArchiveStatus.VALID,
            )
        except (OSError, ValueError) as exc:
            return BackupArchiveEntry(
                **base,
                encrypted=False,
                status=BackupArchiveStatus.INVALID,
                error=str(exc),
            )

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
