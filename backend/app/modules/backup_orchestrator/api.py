from fastapi import APIRouter

from app.core.development_logging import DevelopmentLogService

from .schemas import BackupRunReport, BackupRunRequest
from .service import BackupOrchestratorService

router = APIRouter(prefix="/backup", tags=["Backup Orchestrator"])


@router.post("/run", response_model=BackupRunReport)
def run_backup(request: BackupRunRequest) -> BackupRunReport:
    execution_id = DevelopmentLogService.start_backup(request)
    report = BackupOrchestratorService.run(request)
    DevelopmentLogService.finish_backup(execution_id, request, report)
    return report
