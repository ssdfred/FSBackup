from pathlib import Path

from app.modules.backup_set.repository import BackupSetRepository
from app.modules.backup_set.schemas import BackupSegmentStatus
from app.modules.integrity_engine.schemas import IntegrityReport
from app.modules.integrity_engine.schemas import IntegrityRequest
from app.modules.integrity_engine.service import IntegrityEngineService
from app.modules.restore_engine.schemas import RestoreReport, RestoreRequest
from app.modules.restore_engine.service import RestoreEngineService

from .schemas import RestoreRunReport, RestoreRunRequest


class RestoreOrchestratorService:
    @staticmethod
    def run(request: RestoreRunRequest) -> RestoreRunReport:
        backup_set_directory = RestoreOrchestratorService._backup_set_directory(
            request.archive_path
        )
        if backup_set_directory is not None:
            return RestoreOrchestratorService._run_backup_set(
                request,
                backup_set_directory,
            )
        integrity_report = IntegrityEngineService.verify(
            IntegrityRequest(
                archive_path=request.archive_path,
                password=request.password,
            )
        )
        if not integrity_report.valid:
            return RestoreRunReport(
                archive_path=request.archive_path,
                destination_directory=request.destination_directory,
                integrity_report=integrity_report,
                success=False,
                error="Archive integrity verification failed.",
            )

        restore_report = RestoreEngineService.restore(
            RestoreRequest(
                archive_path=request.archive_path,
                destination_directory=request.destination_directory,
                overwrite=request.overwrite,
                password=request.password,
            )
        )
        return RestoreRunReport(
            archive_path=request.archive_path,
            destination_directory=request.destination_directory,
            integrity_report=integrity_report,
            restore_report=restore_report,
            success=restore_report.success,
            error=restore_report.error,
        )

    @staticmethod
    def _backup_set_directory(archive_path: str) -> Path | None:
        path = Path(archive_path).resolve()
        if path.is_dir() and BackupSetRepository.manifest_path(path).is_file():
            return path
        if path.name.casefold() == BackupSetRepository.MANIFEST_NAME:
            return path.parent
        return None

    @staticmethod
    def _run_backup_set(
        request: RestoreRunRequest,
        backup_set_directory: Path,
    ) -> RestoreRunReport:
        manifest = BackupSetRepository.load(backup_set_directory)
        if manifest is None or not manifest.complete:
            return RestoreOrchestratorService._set_failure(
                request,
                "Backup set is incomplete and cannot be restored as a whole.",
            )

        archive_paths: list[str] = []
        integrity_reports: list[IntegrityReport] = []
        restore_reports: list[RestoreReport] = []
        for segment in manifest.segments:
            if segment.status != BackupSegmentStatus.COMPLETED:
                return RestoreOrchestratorService._set_failure(
                    request,
                    f"Backup segment is not complete: {segment.name}",
                    archive_paths,
                    integrity_reports,
                    restore_reports,
                )
            archive_path = backup_set_directory / segment.archive_name
            archive_paths.append(str(archive_path))
            integrity = IntegrityEngineService.verify(
                IntegrityRequest(
                    archive_path=str(archive_path),
                    password=request.password,
                )
            )
            integrity_reports.append(integrity)
            if not integrity.valid:
                return RestoreOrchestratorService._set_failure(
                    request,
                    f"Backup segment integrity failed: {segment.name}",
                    archive_paths,
                    integrity_reports,
                    restore_reports,
                )
            restored = RestoreEngineService.restore(
                RestoreRequest(
                    archive_path=str(archive_path),
                    destination_directory=request.destination_directory,
                    overwrite=request.overwrite,
                    password=request.password,
                )
            )
            restore_reports.append(restored)
            if not restored.success:
                return RestoreOrchestratorService._set_failure(
                    request,
                    restored.error or f"Backup segment restore failed: {segment.name}",
                    archive_paths,
                    integrity_reports,
                    restore_reports,
                )

        integrity_report = RestoreOrchestratorService._aggregate_integrity(
            request.archive_path,
            integrity_reports,
        )
        restore_report = RestoreOrchestratorService._aggregate_restore(
            request,
            restore_reports,
            success=True,
        )
        return RestoreRunReport(
            archive_path=request.archive_path,
            archive_paths=archive_paths,
            destination_directory=request.destination_directory,
            integrity_report=integrity_report,
            restore_report=restore_report,
            total_segments=len(manifest.segments),
            restored_segments=len(restore_reports),
            success=True,
        )

    @staticmethod
    def _set_failure(
        request: RestoreRunRequest,
        error: str,
        archive_paths: list[str] | None = None,
        integrity_reports: list[IntegrityReport] | None = None,
        restore_reports: list[RestoreReport] | None = None,
    ) -> RestoreRunReport:
        integrity_report = RestoreOrchestratorService._aggregate_integrity(
            request.archive_path,
            integrity_reports or [],
            error=error,
        )
        return RestoreRunReport(
            archive_path=request.archive_path,
            archive_paths=archive_paths or [],
            destination_directory=request.destination_directory,
            integrity_report=integrity_report,
            restore_report=(
                RestoreOrchestratorService._aggregate_restore(
                    request,
                    restore_reports,
                    success=False,
                    error=error,
                )
                if restore_reports
                else None
            ),
            total_segments=len(archive_paths or []),
            restored_segments=len(restore_reports or []),
            success=False,
            error=error,
        )

    @staticmethod
    def _aggregate_integrity(
        archive_path: str,
        reports: list[IntegrityReport],
        error: str | None = None,
    ) -> IntegrityReport:
        errors = [item for report in reports for item in report.errors]
        if error:
            errors.append(error)
        return IntegrityReport(
            archive_path=archive_path,
            valid=bool(reports) and not errors and all(report.valid for report in reports),
            checked_file_count=sum(report.checked_file_count for report in reports),
            missing_files=[item for report in reports for item in report.missing_files],
            unexpected_files=[
                item for report in reports for item in report.unexpected_files
            ],
            size_mismatches=[
                item for report in reports for item in report.size_mismatches
            ],
            errors=errors,
            warnings=[item for report in reports for item in report.warnings],
            duration_ms=sum(report.duration_ms for report in reports),
        )

    @staticmethod
    def _aggregate_restore(
        request: RestoreRunRequest,
        reports: list[RestoreReport],
        success: bool,
        error: str | None = None,
    ) -> RestoreReport:
        return RestoreReport(
            archive_path=request.archive_path,
            destination_directory=request.destination_directory,
            restored_files=sum(report.restored_files for report in reports),
            skipped_files=sum(report.skipped_files for report in reports),
            duration_ms=sum(report.duration_ms for report in reports),
            success=success,
            error=error,
        )
