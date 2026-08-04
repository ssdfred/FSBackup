from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class BackupSegmentStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class BackupSegment(BaseModel):
    index: int = Field(ge=1)
    name: str = Field(min_length=1)
    archive_name: str = Field(min_length=1)
    plan_fingerprint: str = Field(min_length=1)
    status: BackupSegmentStatus = BackupSegmentStatus.PENDING
    file_count: int = Field(default=0, ge=0)
    size_bytes: int = Field(default=0, ge=0)
    archive_size_bytes: int = Field(default=0, ge=0)
    duration_ms: int = Field(default=0, ge=0)
    sha256: str | None = None
    error: str | None = None


class BackupSetManifest(BaseModel):
    format: str = "FSBACKUP_SET"
    format_version: int = 1
    backup_set_id: str = Field(min_length=1)
    archive_name: str = Field(min_length=1)
    source_root: str = Field(min_length=1)
    created_at: datetime
    updated_at: datetime
    segment_size_bytes: int = Field(ge=1)
    encrypted: bool = False
    complete: bool = False
    segments: list[BackupSegment] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
