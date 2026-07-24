"""FastAPI endpoints for Windows source discovery."""

from fastapi import APIRouter, HTTPException, status

from .schemas import SourceDiscoveryReport, SourceDiscoveryRequest
from .service import SourceDiscoveryError, discover_source

router = APIRouter(
    prefix="/sources",
    tags=["Source Discovery"],
)


@router.post(
    "/discover",
    response_model=SourceDiscoveryReport,
    status_code=status.HTTP_200_OK,
)
def discover_windows_source(
    payload: SourceDiscoveryRequest,
) -> SourceDiscoveryReport:
    """Discover users and browser profiles on a Windows disk."""

    try:
        return discover_source(payload.source_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc