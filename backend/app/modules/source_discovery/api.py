"""FastAPI endpoints for Windows source discovery."""

from fastapi import APIRouter, HTTPException, status

from .diagnostic import diagnose_windows_source
from .diagnostic_schemas import WindowsDiagnosticReport, WindowsDiagnosticRequest
from .drives import list_available_drives
from .exclusion_schemas import ExclusionSuggestionReport, ExclusionSuggestionRequest
from .exclusions import suggest_exclusions
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


@router.post(
    "/diagnostic",
    response_model=WindowsDiagnosticReport,
    status_code=status.HTTP_200_OK,
)
def diagnose_selected_windows_source(
    payload: WindowsDiagnosticRequest,
) -> WindowsDiagnosticReport:
    """Estimate recoverable personal data without modifying the source disk."""

    try:
        return diagnose_windows_source(payload.source_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


@router.post(
    "/exclusions/suggestions",
    response_model=ExclusionSuggestionReport,
    status_code=status.HTTP_200_OK,
)
def suggest_source_exclusions(
    payload: ExclusionSuggestionRequest,
) -> ExclusionSuggestionReport:
    """Return conservative exclusion suggestions, all disabled by default."""

    try:
        return suggest_exclusions(payload.source_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
