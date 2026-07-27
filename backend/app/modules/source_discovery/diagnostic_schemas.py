"""Schemas for read-only source diagnostics."""

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


class DiskUsageDiagnostic(BaseModel):
    """Capacity information reported by the filesystem for the selected volume."""

    total_bytes: int = Field(default=0, ge=0)
    used_bytes: int = Field(default=0, ge=0)
    free_bytes: int = Field(default=0, ge=0)


class BackupEstimate(BaseModel):
    """Separate personal-data and actual execution-plan estimates."""

    total_size_bytes: int = 0
    total_file_count: int = 0
    required_free_space_bytes: int = 0
    duration_seconds: int | None = None
    planned_size_bytes: int = 0
    planned_file_count: int = 0
    planned_logical_items: int = 0
    plan_scope: str = "browser_and_profile_data"


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


class CustomFolderDiagnosticRequest(BaseModel):
    """Request for a strict read-only custom-folder diagnostic."""

    source_root: str
    destination_root: str | None = None


class CustomFolderDiagnosticReport(BaseModel):
    """Size and capacity information for a custom backup folder."""

    source_root: str
    destination_root: str | None = None
    size_bytes: int = Field(default=0, ge=0)
    file_count: int = Field(default=0, ge=0)
    source_disk: DiskUsageDiagnostic = Field(default_factory=DiskUsageDiagnostic)
    destination_disk: DiskUsageDiagnostic = Field(default_factory=DiskUsageDiagnostic)
    warnings: list[str] = Field(default_factory=list)


class WindowsDiagnosticReport(BaseModel):
    """Detailed diagnostic displayed before creating a backup."""

    source_root: str
    windows_detected: bool
    confidence: str
    markers: list[WindowsDirectoryMarker] = Field(default_factory=list)
    disk: DiskUsageDiagnostic = Field(default_factory=DiskUsageDiagnostic)
    system: WindowsSystemInformation = Field(default_factory=WindowsSystemInformation)
    users: list[UserProfileDiagnostic] = Field(default_factory=list)
    detected_browsers: list[str] = Field(default_factory=list)
    messaging_profiles: list[MessagingProfileDiagnostic] = Field(default_factory=list)
    applications: list[DetectedApplication] = Field(default_factory=list)
    estimate: BackupEstimate = Field(default_factory=BackupEstimate)
    warnings: list[str] = Field(default_factory=list)
