"""API routes for manifest generation."""

from fastapi import APIRouter, HTTPException, Request, status

from app.modules.execution_planner.schemas import ExecutionPlan

from .schemas import Manifest, ManifestV2
from .service import (
    ManifestBuilderError,
    ManifestBuilderService,
    ManifestV2Builder,
)


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
    """Build a safe, deterministic legacy manifest from an execution plan."""

    try:
        return ManifestBuilderService().build(execution_plan)
    except ManifestBuilderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/v2/build",
    response_model=ManifestV2,
    status_code=status.HTTP_200_OK,
)
def build_manifest_v2(
    execution_plan: ExecutionPlan,
    request: Request,
) -> ManifestV2:
    """Build the versioned Manifest V2 execution contract."""

    try:
        return ManifestV2Builder(
            application_version=str(request.app.version),
        ).build(execution_plan)
    except ManifestBuilderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
