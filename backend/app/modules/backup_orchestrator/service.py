from pathlib import Path
from tempfile import TemporaryDirectory

from app.modules.archive_engine.schemas import ArchiveRequest
from app.modules.archive_engine.service import ArchiveEngineService
from app.modules.copy_engine.schemas import CopyRequest
from app.modules.copy_engine.service import CopyEngineService
from app.modules.execution_planner.service import ExecutionPlannerService
from app.modules.integrity_engine.schemas import IntegrityRequest
from app.modules.integrity_engine.service import IntegrityEngineService
from app.modules.manifest_builder.service import ManifestBuilderService

from .schemas import BackupRunReport, BackupRunRequest


class BackupOrchestratorService:
    @classmethod
    def run(cls, request: BackupRunRequest) -> BackupRunReport:
        try:
            execution_plan = ExecutionPlannerService().build_plan(
                request.source_root,
                request.selected_item_ids,
            )
            with TemporaryDirectory(prefix="fsbackup-") as workspace:
                copy_report = CopyEngineService.execute(
                    CopyRequest(
                        execution_plan=execution_plan,
                        destination_root=workspace,
                    )
                )
                warnings = [issue.message for issue in copy_report.warnings]
                if not copy_report.success:
                    error = copy_report.errors[0].message if copy_report.errors else "Copy failed."
                    return BackupRunReport(
                        success=False,
                        copied_files=copy_report.summary.copied,
                        warnings=warnings,
                        error=error,
                        copy_report=copy_report,
                    )

                manifest = ManifestBuilderService().build(execution_plan)
                archive_report = ArchiveEngineService.create(
                    ArchiveRequest(
                        source_directory=workspace,
                        destination_directory=request.destination_directory,
                        archive_name=request.archive_name,
                        manifest=manifest,
                        compression=request.compression,
                        encryption=request.encryption,
                    )
                )
                if not archive_report.success:
                    return BackupRunReport(
                        success=False,
                        copied_files=copy_report.summary.copied,
                        warnings=warnings,
                        error=archive_report.error,
                        copy_report=copy_report,
                        archive_report=archive_report,
                    )

                integrity_report = None
                if request.verify_integrity:
                    password = request.encryption.password if request.encryption else None
                    integrity_report = IntegrityEngineService.verify(
                        IntegrityRequest(
                            archive_path=archive_report.archive_path,
                            password=password,
                        )
                    )
                    if not integrity_report.valid:
                        Path(archive_report.archive_path).unlink(missing_ok=True)
                        return BackupRunReport(
                            success=False,
                            copied_files=copy_report.summary.copied,
                            warnings=warnings + integrity_report.warnings,
                            error="Archive integrity verification failed.",
                            copy_report=copy_report,
                            archive_report=archive_report,
                            integrity_report=integrity_report,
                        )

                return BackupRunReport(
                    success=True,
                    archive_path=archive_report.archive_path,
                    copied_files=copy_report.summary.copied,
                    warnings=warnings,
                    copy_report=copy_report,
                    archive_report=archive_report,
                    integrity_report=integrity_report,
                )
        except (OSError, ValueError) as exc:
            return BackupRunReport(success=False, error=str(exc))
