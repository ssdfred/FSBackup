from fastapi import APIRouter

from .schemas import BackupRunReport, BackupRunRequest
from .service import BackupOrchestratorService

router = APIRouter(prefix="/backup", tags=["Backup Orchestrator"])


@router.post("/run", response_model=BackupRunReport)
def run_backup(request: BackupRunRequest) -> BackupRunReport:
    return BackupOrchestratorService.run(request)
