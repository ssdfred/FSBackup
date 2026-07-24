from datetime import datetime

from pydantic import BaseModel

from app.modules.manifest_builder.schemas import Manifest


class ArchiveRequest(BaseModel):
    source_directory: str
    destination_directory: str
    archive_name: str
    manifest: Manifest


class ArchiveMetadata(BaseModel):
    format: str = "FSB"
    format_version: int = 1
    application: str = "FSBackup"
    application_version: str = "0.3.0"
    created_at: datetime
    platform: str


class ArchiveReport(BaseModel):
    archive_path: str
    file_count: int
    archive_size: int
    duration_ms: int
    success: bool
    error: str | None = None
