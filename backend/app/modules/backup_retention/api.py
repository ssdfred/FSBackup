from fastapi import APIRouter

from .schemas import RetentionSimulationReport, RetentionSimulationRequest
from .service import BackupRetentionService

router = APIRouter(prefix="/backups/retention", tags=["Backup Retention"])


@router.post("/simulate", response_model=RetentionSimulationReport)
def simulate_retention(
    request: RetentionSimulationRequest,
) -> RetentionSimulationReport:
    return BackupRetentionService.simulate(request)
