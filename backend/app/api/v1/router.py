from fastapi import APIRouter

from app.modules.backup_planner.api import router as backup_planner_router
from app.modules.browser_inspector.api import router as browser_inspector_router
from app.modules.source_discovery.api import router as source_discovery_router

from app.modules.execution_planner.api import (
    router as execution_planner_router,
)
from app.modules.copy_engine.api import router as copy_engine_router

router = APIRouter(prefix="/api/v1")

router.include_router(browser_inspector_router)
router.include_router(source_discovery_router)
router.include_router(execution_planner_router)
router.include_router(backup_planner_router)
router.include_router(copy_engine_router)

@router.get("/test")
def test():
    return {"message": "OK"}