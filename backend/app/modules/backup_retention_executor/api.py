from fastapi import APIRouter

from .schemas import RetentionExecutionReport, RetentionExecutionRequest
from .service import BackupRetentionExecutorService

router = APIRouter(prefix="/backups/retention", tags=["Backup Retention"])


@router.post("/execute", response_model=RetentionExecutionReport)
def execute_retention(request: RetentionExecutionRequest) -> RetentionExecutionReport:
    return BackupRetentionExecutorService.execute(request)
