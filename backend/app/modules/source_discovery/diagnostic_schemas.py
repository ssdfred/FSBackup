"""Schemas for the read-only Windows source diagnostic."""

from __future__ import annotations

from pydantic import BaseModel, Field


class WindowsDirectoryMarker(BaseModel):
    """Presence of one expected Windows installation directory."""

    name: str
    path: str
    present: bool
    required: bool = True


class FolderEstimate(BaseModel):
    """Read-only size and file-count estimate for one directory."""

    name: str
    path: str
    present: bool
    size_bytes: int = 0
    file_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class UserProfileDiagnostic(BaseModel):
    """Recoverable personal folders detected for one Windows profile."""

    name: str
    path: str
    folders: list[FolderEstimate] = Field(default_factory=list)
    total_size_bytes: int = 0
    total_file_count: int = 0


class BackupEstimate(BaseModel):
    """Global source estimate before any user-approved exclusion."""

    total_size_bytes: int = 0
    total_file_count: int = 0
    required_free_space_bytes: int = 0
    duration_seconds: int | None = None


class WindowsSystemInformation(BaseModel):
    """Optional information recoverable without modifying the source."""

    version: str | None = None
    edition: str | None = None
    architecture: str | None = None
    computer_name: str | None = None
    installation_date: str | None = None
    system_size_bytes: int | None = None


class DetectedApplication(BaseModel):
    """Application inferred from standard installation or user-data paths."""

    key: str
    name: str
    detected_paths: list[str] = Field(default_factory=list)


class MessagingProfileDiagnostic(BaseModel):
    """Useful mail-client data detected for one Windows profile."""

    client: str
    user_name: str
    paths: list[str] = Field(default_factory=list)
    size_bytes: int = 0
    file_count: int = 0
    warnings: list[str] = Field(default_factory=list)


class WindowsDiagnosticRequest(BaseModel):
    """Request for a strict read-only source diagnostic."""

    source_root: str


class WindowsDiagnosticReport(BaseModel):
    """Detailed diagnostic displayed before creating a backup."""

    source_root: str
    windows_detected: bool
    confidence: str
    markers: list[WindowsDirectoryMarker] = Field(default_factory=list)
    system: WindowsSystemInformation = Field(default_factory=WindowsSystemInformation)
    users: list[UserProfileDiagnostic] = Field(default_factory=list)
    detected_browsers: list[str] = Field(default_factory=list)
    messaging_profiles: list[MessagingProfileDiagnostic] = Field(default_factory=list)
    applications: list[DetectedApplication] = Field(default_factory=list)
    estimate: BackupEstimate = Field(default_factory=BackupEstimate)
    warnings: list[str] = Field(default_factory=list)
