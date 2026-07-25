from fastapi import APIRouter

from .schemas import UiCapability, UiDashboardSummary

router = APIRouter(prefix="/dashboard", tags=["interface"])


@router.get("/summary", response_model=UiDashboardSummary)
def dashboard_summary() -> UiDashboardSummary:
    return UiDashboardSummary(
        api_version="v1",
        capabilities=[
            UiCapability(
                key="backup",
                label="Create a backup",
                endpoint="/api/v1/backup/run",
                method="POST",
            ),
            UiCapability(
                key="catalog",
                label="Browse local backups",
                endpoint="/api/v1/backups/catalog",
                method="POST",
            ),
            UiCapability(
                key="restore",
                label="Restore a backup",
                endpoint="/api/v1/restore/run",
                method="POST",
            ),
            UiCapability(
                key="retention_simulation",
                label="Simulate retention",
                endpoint="/api/v1/backups/retention/simulate",
                method="POST",
            ),
            UiCapability(
                key="retention_execution",
                label="Execute confirmed retention",
                endpoint="/api/v1/backups/retention/execute",
                method="POST",
                destructive=True,
            ),
        ],
    )
