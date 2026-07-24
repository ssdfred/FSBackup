"""API routes for manifest generation."""

from fastapi import APIRouter, HTTPException, status

from app.modules.execution_planner.schemas import ExecutionPlan

from .schemas import Manifest
from .service import ManifestBuilderError, ManifestBuilderService


router = APIRouter(
    prefix="/manifests",
    tags=["Manifest builder"],
)


@router.post(
    "/build",
    response_model=Manifest,
    status_code=status.HTTP_200_OK,
)
def build_manifest(execution_plan: ExecutionPlan) -> Manifest:
    """Build a safe, deterministic manifest from an execution plan."""

    try:
        return ManifestBuilderService().build(execution_plan)
    except ManifestBuilderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
