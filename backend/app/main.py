from fastapi import FastAPI

from app.api.v1.router import router as v1_router

app = FastAPI(
    title="FSBackup",
    version="0.1.0",
    description="Backup, migration and workstation audit platform.",
)

app.include_router(v1_router)

@app.get("/")
def root():
    return {
        "application": "FSBackup",
        "status": "running",
        "version": "0.1.0",
    }
