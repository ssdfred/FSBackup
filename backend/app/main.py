from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles

from app.api.v1.router import router as v1_router
from app.core.api_errors import register_error_handlers
from app.version import __version__

app = FastAPI(
    title="FSBackup",
    version=__version__,
    description="Backup, migration and workstation audit platform.",
)


@app.middleware("http")
async def disable_web_ui_cache(request: Request, call_next) -> Response:
    """Prevent stale UI modules from surviving an application update."""

    response = await call_next(request)
    if request.url.path.startswith("/app"):
        response.headers["Cache-Control"] = (
            "no-store, no-cache, must-revalidate, max-age=0"
        )
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


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
