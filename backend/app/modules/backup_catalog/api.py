from fastapi import APIRouter

from .schemas import BackupCatalogReport, BackupCatalogRequest
from .service import BackupCatalogService

router = APIRouter(prefix="/backups", tags=["Backup Catalog"])


@router.post("/catalog", response_model=BackupCatalogReport)
def catalog_backups(request: BackupCatalogRequest) -> BackupCatalogReport:
    return BackupCatalogService.scan(request)
