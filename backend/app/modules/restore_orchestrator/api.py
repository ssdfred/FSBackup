from fastapi import APIRouter

from .schemas import RestoreRunReport, RestoreRunRequest
from .service import RestoreOrchestratorService

router = APIRouter(prefix="/restore", tags=["Restore Orchestrator"])


@router.post("/run", response_model=RestoreRunReport)
def run_restore(request: RestoreRunRequest) -> RestoreRunReport:
    return RestoreOrchestratorService.run(request)
