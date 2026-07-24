from datetime import datetime

from pydantic import BaseModel, Field


class ManifestFile(BaseModel):
    relative_path: str
    size: int
    mandatory: bool
    potentially_locked: bool
    required_by: list[str] = Field(default_factory=list)


class ManifestSummary(BaseModel):
    logical_items: int
    physical_files: int
    missing_files: int
    encrypted_items: int
    deduplicated_files: int
    estimated_size_bytes: int
    warnings: int


class Manifest(BaseModel):
    format_version: int = 1
    created_at: datetime
    source_root: str

    summary: ManifestSummary

    files: list[ManifestFile] = Field(default_factory=list)