from pydantic import BaseModel, Field


class IntegrityRequest(BaseModel):
    archive_path: str


class IntegrityReport(BaseModel):
    archive_path: str
    valid: bool
    checked_file_count: int = 0
    missing_files: list[str] = Field(default_factory=list)
    unexpected_files: list[str] = Field(default_factory=list)
    size_mismatches: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    duration_ms: int
