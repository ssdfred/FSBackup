"""FastAPI endpoints for Windows source discovery."""

from fastapi import APIRouter, HTTPException, status

from .drives import list_available_drives
from .schemas import (
    AvailableDrivesReport,
    SourceDiscoveryReport,
    SourceDiscoveryRequest,
)
from .service import SourceDiscoveryError, discover_source

router = APIRouter(
    prefix="/sources",
    tags=["Source Discovery"],
)


@router.get(
    "/drives",
    response_model=AvailableDrivesReport,
    status_code=status.HTTP_200_OK,
)
def get_available_drives() -> AvailableDrivesReport:
    """List mounted drive roots available as backup sources."""

    return list_available_drives()


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
