"""FastAPI endpoints for source discovery."""

from pathlib import Path
import shutil

from fastapi import APIRouter, HTTPException, status

from app.modules.execution_planner.windows_service import WindowsExecutionPlannerService

from .diagnostic import diagnose_windows_source
from .diagnostic_schemas import (
    CustomFolderDiagnosticReport,
    CustomFolderDiagnosticRequest,
    DiskUsageDiagnostic,
    WindowsDiagnosticReport,
    WindowsDiagnosticRequest,
)
from .drives import list_available_drives
from .exclusion_schemas import ExclusionSuggestionReport, ExclusionSuggestionRequest
from .exclusions import suggest_exclusions
from .folder_diagnostic import diagnose_custom_folder
from .root_inventory import inventory_root
from .root_inventory_schemas import RootInventoryReport, RootInventoryRequest
from .schemas import (
    AvailableDrivesReport,
    SourceDiscoveryReport,
    SourceDiscoveryRequest,
)
from .service import SourceDiscoveryError, discover_source

router = APIRouter(prefix="/sources", tags=["Source Discovery"])


@router.get("/drives", response_model=AvailableDrivesReport, status_code=status.HTTP_200_OK)
def get_available_drives() -> AvailableDrivesReport:
    return list_available_drives()


@router.post("/discover", response_model=SourceDiscoveryReport, status_code=status.HTTP_200_OK)
def discover_windows_source(payload: SourceDiscoveryRequest) -> SourceDiscoveryReport:
    try:
        return discover_source(payload.source_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/diagnostic", response_model=WindowsDiagnosticReport, status_code=status.HTTP_200_OK)
def diagnose_selected_windows_source(
    payload: WindowsDiagnosticRequest,
) -> WindowsDiagnosticReport:
    """Describe disk usage, personal data and the default Windows backup plan."""

    try:
        report = diagnose_windows_source(payload.source_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    root = Path(report.source_root)
    try:
        usage = shutil.disk_usage(root)
        report.disk = DiskUsageDiagnostic(
            total_bytes=usage.total,
            used_bytes=usage.used,
            free_bytes=usage.free,
        )
    except OSError as exc:
        report.warnings.append(
            f"Impossible de mesurer l'espace du lecteur {root} : {exc}"
        )

    try:
        plan = WindowsExecutionPlannerService.build_plan(root)
        report.estimate.planned_size_bytes = plan.summary.estimated_size_bytes
        report.estimate.planned_file_count = plan.summary.physical_files
        report.estimate.planned_logical_items = plan.summary.logical_items
        report.estimate.required_free_space_bytes = plan.summary.estimated_size_bytes
        report.estimate.plan_scope = "personal_browser_and_selected_projects"
    except (OSError, ValueError) as exc:
        report.warnings.append(
            "Le plan réel de sauvegarde n'a pas pu être estimé : " f"{exc}"
        )

    return report


@router.post(
    "/folder-diagnostic",
    response_model=CustomFolderDiagnosticReport,
    status_code=status.HTTP_200_OK,
)
def diagnose_selected_custom_folder(
    payload: CustomFolderDiagnosticRequest,
) -> CustomFolderDiagnosticReport:
    """Measure a custom source folder and the selected destination capacity."""

    try:
        return diagnose_custom_folder(payload.source_root, payload.destination_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/root-inventory",
    response_model=RootInventoryReport,
    status_code=status.HTTP_200_OK,
)
def inventory_selected_source_root(
    payload: RootInventoryRequest,
) -> RootInventoryReport:
    try:
        return inventory_root(payload.source_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post(
    "/exclusions/suggestions",
    response_model=ExclusionSuggestionReport,
    status_code=status.HTTP_200_OK,
)
def suggest_source_exclusions(
    payload: ExclusionSuggestionRequest,
) -> ExclusionSuggestionReport:
    try:
        return suggest_exclusions(payload.source_root)
    except SourceDiscoveryError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
