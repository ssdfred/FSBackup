from app.modules.integrity_engine.schemas import IntegrityRequest
from app.modules.integrity_engine.service import IntegrityEngineService
from app.modules.restore_engine.schemas import RestoreRequest
from app.modules.restore_engine.service import RestoreEngineService

from .schemas import RestoreRunReport, RestoreRunRequest


class RestoreOrchestratorService:
    @staticmethod
    def run(request: RestoreRunRequest) -> RestoreRunReport:
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
