from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from ..browser_inspector.schemas import BrowserProfile


class BrowserBackupEntry(BaseModel):
    """Browser entry persisted in the backup manifest."""

    name: str
    version: str | None = None
    profiles: list[BrowserProfile] = Field(default_factory=list)


class BackupManifest(BaseModel):
    """Top-level backup manifest payload."""

    format_version: int
    created_at: datetime
    application: str
    application_version: str
    machine_name: str
    platform: str
    browsers: list[BrowserBackupEntry] = Field(default_factory=list)


class BackupMetadata(BaseModel):
    """Supplementary metadata for the backup structure."""

    browser_count: int
    profile_count: int
    created_at: datetime