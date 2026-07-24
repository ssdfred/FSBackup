"""API routes for physical execution planning."""

from fastapi import APIRouter, HTTPException, status

from .schemas import ExecutionPlan, ExecutionPlanRequest
from .service import ExecutionPlannerError, ExecutionPlannerService


router = APIRouter(
    prefix="/execution",
    tags=["Execution planner"],
)


@router.post(
    "/plan",
    response_model=ExecutionPlan,
    status_code=status.HTTP_200_OK,
)
def create_execution_plan(
    request: ExecutionPlanRequest,
) -> ExecutionPlan:
    """Build a read-only physical execution plan."""

    try:
        return ExecutionPlannerService().build_plan(
            source_root=request.source_root,
            selected_item_ids=request.selected_item_ids,
        )
    except ExecutionPlannerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except (FileNotFoundError, NotADirectoryError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source de sauvegarde invalide : {exc}",
        ) from exc