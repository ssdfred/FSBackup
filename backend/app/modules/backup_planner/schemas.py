"""Pydantic schemas for intelligent backup planning."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from app.modules.source_discovery.schemas import SourceType


class BackupPriority(StrEnum):
    """Importance assigned to a logical backup item."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    OPTIONAL = "optional"
    IGNORE = "ignore"


class BackupItem(BaseModel):
    """A logical item that may be included in a backup."""

    id: str
    category: str
    title: str
    selected: bool
    priority: BackupPriority
    reason: str
    encrypted: bool = False
    estimated_size_bytes: int = Field(default=0, ge=0)
    estimated_files: int = Field(default=0, ge=0)


class BackupProfile(BaseModel):
    """Backup plan for one application profile."""

    name: str
    source_path: str
    items: list[BackupItem] = Field(default_factory=list)


class BackupApplication(BaseModel):
    """Backup plan for one discovered application."""

    key: str
    name: str
    profiles: list[BackupProfile] = Field(default_factory=list)


class BackupUser(BaseModel):
    """Backup plan for one Windows user."""

    name: str
    source_path: str
    applications: list[BackupApplication] = Field(default_factory=list)


class BackupPlanSummary(BaseModel):
    """Aggregated information about a backup plan."""

    users: int = Field(default=0, ge=0)
    applications: int = Field(default=0, ge=0)
    profiles: int = Field(default=0, ge=0)
    items: int = Field(default=0, ge=0)
    selected_items: int = Field(default=0, ge=0)
    excluded_items: int = Field(default=0, ge=0)
    encrypted_items: int = Field(default=0, ge=0)
    estimated_size_bytes: int = Field(default=0, ge=0)
    estimated_files: int = Field(default=0, ge=0)


class BackupPlanRequest(BaseModel):
    """Request used to generate a backup plan."""

    source_root: str = Field(
        ...,
        min_length=1,
        examples=["E:\\"],
        description="Root of the Windows disk to inspect.",
    )


class BackupPlan(BaseModel):
    """Complete intelligent backup plan."""

    source_root: str
    source_type: SourceType
    windows_detected: bool
    users: list[BackupUser] = Field(default_factory=list)
    summary: BackupPlanSummary
    warnings: list[str] = Field(default_factory=list)