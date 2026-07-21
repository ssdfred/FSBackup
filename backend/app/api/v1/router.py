from fastapi import APIRouter

from app.modules.browser_inspector.api import router as browser_inspector_router

router = APIRouter(prefix="/api/v1")

router.include_router(browser_inspector_router)


@router.get("/test")
def test():
    return {"message": "OK"}