from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ManifestFile(BaseModel):
    """Physical file referenced by a backup manifest."""

    relative_path: str
    size: int = Field(ge=0)
    mandatory: bool
    potentially_locked: bool
    required_by: list[str] = Field(default_factory=list)


class ManifestSummary(BaseModel):
    """Legacy Manifest V1 summary kept for backward compatibility."""

    logical_items: int
    physical_files: int
    missing_files: int
    encrypted_items: int
    deduplicated_files: int
    estimated_size_bytes: int
    warnings: int


class Manifest(BaseModel):
    """Manifest V1 contract kept readable during the V2 migration."""

    format_version: int = 1
    created_at: datetime
    source_root: str
    summary: ManifestSummary
    files: list[ManifestFile] = Field(default_factory=list)


class ManifestHeader(BaseModel):
    """Identity and version information for a Manifest V2 document."""

    format_version: Literal[2] = 2
    manifest_id: str = Field(min_length=1)
    created_at: datetime
    application: str = "FSBackup"
    application_version: str = Field(min_length=1)


class SourceInfo(BaseModel):
    """Description of a logical source included in the backup."""

    source_id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    source_type: str = Field(min_length=1)
    display_name: str = Field(min_length=1)
    original_path: str | None = None
    required: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class BrowserInfo(BaseModel):
    """Browser-specific information persisted when applicable."""

    name: str = Field(min_length=1)
    version: str | None = None
    profile_names: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionInfo(BaseModel):
    """Execution context used to create the backup."""

    execution_id: str = Field(min_length=1)
    started_at: datetime
    completed_at: datetime | None = None
    status: Literal["planned", "running", "completed", "partial", "failed"] = "planned"
    machine_name: str | None = None
    platform: str | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class Statistics(BaseModel):
    """Aggregated backup statistics."""

    source_count: int = Field(default=0, ge=0)
    logical_items: int = Field(default=0, ge=0)
    physical_files: int = Field(default=0, ge=0)
    copied_files: int = Field(default=0, ge=0)
    missing_files: int = Field(default=0, ge=0)
    skipped_files: int = Field(default=0, ge=0)
    failed_files: int = Field(default=0, ge=0)
    total_size_bytes: int = Field(default=0, ge=0)
    copied_size_bytes: int = Field(default=0, ge=0)
    duration_seconds: float | None = Field(default=None, ge=0)


class IntegrityInfo(BaseModel):
    """Integrity strategy and verification result for a backup."""

    algorithm: str = Field(default="sha256", min_length=1)
    checked: bool = False
    verified_at: datetime | None = None
    expected_files: int = Field(default=0, ge=0)
    verified_files: int = Field(default=0, ge=0)
    failed_files: int = Field(default=0, ge=0)
    report_path: str | None = None


class ManifestMetadata(BaseModel):
    """Extensible metadata that does not alter the core contract."""

    tags: list[str] = Field(default_factory=list)
    notes: str | None = None
    custom: dict[str, Any] = Field(default_factory=dict)


class ManifestV2(BaseModel):
    """Central, versioned contract shared by FSBackup engines."""

    header: ManifestHeader
    execution: ExecutionInfo
    sources: list[SourceInfo] = Field(default_factory=list)
    browsers: list[BrowserInfo] = Field(default_factory=list)
    files: list[ManifestFile] = Field(default_factory=list)
    statistics: Statistics = Field(default_factory=Statistics)
    integrity: IntegrityInfo = Field(default_factory=IntegrityInfo)
    metadata: ManifestMetadata = Field(default_factory=ManifestMetadata)
