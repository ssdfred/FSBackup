from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as v1_router
from app.core.api_errors import register_error_handlers

app = FastAPI(
    title="FSBackup",
    version="0.1.0",
    description="Backup, migration and workstation audit platform.",
)

register_error_handlers(app)
app.include_router(v1_router)

WEB_UI_DIRECTORY = Path(__file__).resolve().parent / "web_ui"
app.mount("/app", StaticFiles(directory=WEB_UI_DIRECTORY, html=True), name="web-ui")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/app/")
