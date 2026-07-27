from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
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
REQUIRED_UI_MODULES = (
    "diagnostic_source_guard.js",
    "capacity.js",
    "root_inventory.js",
    "exclusion_payload.js",
    "backup_validation_report.js",
    "drive_capacity_bridge.js",
    "backup_layout.js",
    "exclusion_confirmation_summary.js",
    "source_mode_cleanup.js",
    "custom_folder_capacity.js",
    "exclusion_summary_layout.js",
)
UI_MODULE_VERSION = "10.8.10"


@app.get("/app/", include_in_schema=False)
def web_ui_index() -> HTMLResponse:
    """Serve the UI with critical optional modules pinned into the document."""

    html = (WEB_UI_DIRECTORY / "index.html").read_text(encoding="utf-8")
    required_scripts = "\n".join(
        f'<script src="/app/{module}?v={UI_MODULE_VERSION}" defer '
        f'data-fsbackup-required="{module}"></script>'
        for module in REQUIRED_UI_MODULES
    )
    html = html.replace("</body>", f"{required_scripts}\n</body>")
    return HTMLResponse(html)


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
