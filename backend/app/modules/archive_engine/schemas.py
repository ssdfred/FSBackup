from datetime import datetime

from pydantic import BaseModel, Field

from app.modules.compression_engine.schemas import (
    CompressionMethod,
    CompressionSettings,
)
from app.modules.encryption_engine.schemas import EncryptionSettings
from app.modules.manifest_builder.schemas import Manifest


class ArchiveRequest(BaseModel):
    source_directory: str
    destination_directory: str
    archive_name: str
    manifest: Manifest
    compression: CompressionSettings = Field(default_factory=CompressionSettings)
    encryption: EncryptionSettings | None = None


class ArchiveMetadata(BaseModel):
    format: str = "FSB"
    format_version: int = 1
    application: str = "FSBackup"
    application_version: str = "0.6.0"
    created_at: datetime
    platform: str
    compression_method: CompressionMethod = CompressionMethod.DEFLATED
    compression_level: int = 6


class ArchiveReport(BaseModel):
    archive_path: str
    file_count: int
    archive_size: int
    original_size: int = 0
    saved_bytes: int = 0
    compression_ratio: float = 0.0
    compression_method: CompressionMethod = CompressionMethod.DEFLATED
    compression_level: int = 6
    encrypted: bool = False
    duration_ms: int
    success: bool
    error: str | None = None
