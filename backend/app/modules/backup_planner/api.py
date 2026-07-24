"""FastAPI routes for intelligent backup planning."""

from fastapi import APIRouter, HTTPException, status

from app.modules.source_discovery.service import SourceDiscoveryError

from .schemas import BackupPlan, BackupPlanRequest
from .service import BackupPlannerService

router = APIRouter(
    prefix="/backup",
    tags=["Backup planner"],
)

planner_service = BackupPlannerService()


@router.post(
    "/plan",
    response_model=BackupPlan,
    status_code=status.HTTP_200_OK,
)
def create_backup_plan(
    request: BackupPlanRequest,
) -> BackupPlan:
    """Generate a read-only intelligent backup plan."""

    try:
        return planner_service.build_plan(request.source_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc