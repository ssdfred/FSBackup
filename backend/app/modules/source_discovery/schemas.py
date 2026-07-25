"""Pydantic schemas for Windows source discovery."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    """Supported source types."""

    LOCAL_WINDOWS = "local_windows"
    WINDOWS_DISK = "windows_disk"


class AvailableDrive(BaseModel):
    """A mounted filesystem root available as a backup source."""

    root: str
    label: str
    system: bool = False


class AvailableDrivesReport(BaseModel):
    """Mounted filesystem roots detected by FSBackup."""

    drives: list[AvailableDrive] = Field(default_factory=list)


class DataAvailability(BaseModel):
    """Availability of useful browser data inside a profile."""

    bookmarks: bool = False
    history: bool = False
    cookies: bool = False
    passwords: bool = False
    autofill: bool = False
    extensions: bool = False
    sessions: bool = False
    preferences: bool = False
    potentially_encrypted: list[str] = Field(default_factory=list)


class DiscoveredBrowserProfile(BaseModel):
    """A browser profile found on the source disk."""

    name: str
    path: str
    data: DataAvailability


class DiscoveredBrowser(BaseModel):
    """A browser installation or data directory found for a user."""

    key: str
    name: str
    profile_root: str
    profiles: list[DiscoveredBrowserProfile] = Field(default_factory=list)


class DiscoveredUser(BaseModel):
    """A Windows user found on the source disk."""

    name: str
    path: str
    browsers: list[DiscoveredBrowser] = Field(default_factory=list)


class SourceDiscoveryRequest(BaseModel):
    """Request used to inspect a Windows source disk."""

    source_root: str = Field(
        ...,
        min_length=1,
        examples=["E:\\"],
        description="Root of the Windows disk to inspect.",
    )


class SourceDiscoveryReport(BaseModel):
    """Complete read-only discovery report."""

    source_root: str
    source_type: SourceType
    windows_detected: bool
    users_directory: str | None = None
    users: list[DiscoveredUser] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
