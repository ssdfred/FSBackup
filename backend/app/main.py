from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as v1_router
from app.core.api_errors import register_error_handlers
from app.version import __version__

app = FastAPI(
    title="FSBackup",
    version=__version__,
    description="Backup, migration and workstation audit platform.",
)

register_error_handlers(app)
app.include_router(v1_router)

WEB_UI_DIRECTORY = Path(__file__).resolve().parent / "web_ui"
app.mount("/app", StaticFiles(directory=WEB_UI_DIRECTORY, html=True), name="web-ui")


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(
        WEB_UI_DIRECTORY / "favicon.svg",
        media_type="image/svg+xml",
    )


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/app/")
