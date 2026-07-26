"""Schemas for the read-only inventory of a Windows volume root."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RootEntryCategory(StrEnum):
    """Safety-oriented classification of a root-level entry."""

    PERSONAL = "données_personnelles"
    REVIEW = "à_examiner"
    SYSTEM = "système_non_inclus"
    OLD_WINDOWS = "ancienne_installation_windows"


class RootInventoryEntry(BaseModel):
    """One visible root-level directory classified without modifying it."""

    name: str
    path: str
    category: RootEntryCategory
    reason: str
    included_by_default: bool = False
    size_bytes: int | None = None
    file_count: int | None = None
    warnings: list[str] = Field(default_factory=list)


class WindowsRecoveryProfile(BaseModel):
    """Recoverable content found in one current or legacy Windows profile."""

    name: str
    path: str
    profile_kind: str
    standard_size_bytes: int = 0
    standard_file_count: int = 0
    total_size_bytes: int = 0
    total_file_count: int = 0
    additional_size_bytes: int = 0
    additional_file_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class RootInventoryRequest(BaseModel):
    source_root: str = Field(min_length=1)


class RootInventoryReport(BaseModel):
    """Read-only root inventory shown independently from backup selection."""

    source_root: str
    entries: list[RootInventoryEntry] = Field(default_factory=list)
    current_windows_profiles: list[WindowsRecoveryProfile] = Field(default_factory=list)
    old_windows_profiles: list[WindowsRecoveryProfile] = Field(default_factory=list)
    review_size_bytes: int = 0
    review_file_count: int = 0
    recoverable_profile_size_bytes: int = 0
    recoverable_profile_file_count: int = 0
    warnings: list[str] = Field(default_factory=list)
