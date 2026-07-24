from fastapi import APIRouter

from app.modules.browser_inspector.api import router as browser_inspector_router
from app.modules.source_discovery.api import router as source_discovery_router

router = APIRouter(prefix="/api/v1")

router.include_router(browser_inspector_router)
router.include_router(source_discovery_router)


@router.get("/test")
def test():
    return {"message": "OK"}