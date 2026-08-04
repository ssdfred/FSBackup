from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field, SecretStr


class BackupArchiveStatus(StrEnum):
    VALID = "valid"
    INVALID = "invalid"
    PASSWORD_REQUIRED = "password_required"


class BackupCatalogRequest(BaseModel):
    directory: str = Field(min_length=1)
    recursive: bool = False
    password: SecretStr | None = None


class BackupArchiveEntry(BaseModel):
    path: str
    name: str
    encrypted: bool
    size_bytes: int = Field(ge=0)
    modified_at: datetime
    status: BackupArchiveStatus
    created_at: datetime | None = None
    application_version: str | None = None
    file_count: int | None = Field(default=None, ge=0)
    original_size_bytes: int | None = Field(default=None, ge=0)
    error: str | None = None
    backup_set: bool = False
    segment_count: int = Field(default=0, ge=0)
    completed_segments: int = Field(default=0, ge=0)


class BackupCatalogSummary(BaseModel):
    total: int = Field(ge=0)
    valid: int = Field(ge=0)
    invalid: int = Field(ge=0)
    password_required: int = Field(ge=0)
    encrypted: int = Field(ge=0)
    total_size_bytes: int = Field(ge=0)


class BackupCatalogReport(BaseModel):
    directory: str
    archives: list[BackupArchiveEntry] = Field(default_factory=list)
    summary: BackupCatalogSummary
    warnings: list[str] = Field(default_factory=list)
