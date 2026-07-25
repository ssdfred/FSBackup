from fastapi import FastAPI

from app.api.v1.router import router as v1_router
from app.core.api_errors import register_error_handlers

app = FastAPI(
    title="FSBackup",
    version="0.1.0",
    description="Backup, migration and workstation audit platform.",
)

register_error_handlers(app)
app.include_router(v1_router)


@app.get("/")
def root():
    return {
        "application": "FSBackup",
        "status": "running",
        "version": "0.1.0",
    }
