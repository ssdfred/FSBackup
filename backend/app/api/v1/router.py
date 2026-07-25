from fastapi import APIRouter

from app.modules.archive_engine.api import router as archive_engine_router
from app.modules.backup_catalog.api import router as backup_catalog_router
from app.modules.backup_orchestrator.api import router as backup_orchestrator_router
from app.modules.backup_planner.api import router as backup_planner_router
from app.modules.backup_retention.api import router as backup_retention_router
from app.modules.browser_inspector.api import router as browser_inspector_router
from app.modules.copy_engine.api import router as copy_engine_router
from app.modules.execution_planner.api import (
    router as execution_planner_router,
)
from app.modules.integrity_engine.api import router as integrity_engine_router
from app.modules.manifest_builder.api import router as manifest_builder_router
from app.modules.restore_engine.api import router as restore_engine_router
from app.modules.restore_orchestrator.api import router as restore_orchestrator_router
from app.modules.source_discovery.api import router as source_discovery_router

router = APIRouter(prefix="/api/v1")

router.include_router(browser_inspector_router)
router.include_router(source_discovery_router)
router.include_router(execution_planner_router)
router.include_router(backup_planner_router)
router.include_router(manifest_builder_router)
router.include_router(copy_engine_router)
router.include_router(archive_engine_router)
router.include_router(backup_orchestrator_router)
router.include_router(backup_catalog_router)
router.include_router(backup_retention_router)
router.include_router(restore_engine_router)
router.include_router(restore_orchestrator_router)
router.include_router(integrity_engine_router)


@router.get("/test")
def test():
    return {"message": "OK"}
