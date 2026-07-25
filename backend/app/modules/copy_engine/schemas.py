from enum import StrEnum

from pydantic import BaseModel, Field

from app.modules.execution_planner.schemas import ExecutionPlan


class CopyStatus(StrEnum):
    COPIED = "copied"
    SKIPPED = "skipped"
    MISSING = "missing"
    ERROR = "error"


class CopyRequest(BaseModel):
    execution_plan: ExecutionPlan
    destination_root: str = Field(min_length=1)


class CopyFileResult(BaseModel):
    source: str
    destination: str
    status: CopyStatus
    size: int = 0
    duration_ms: int = 0
    error: str | None = None


class CopySummary(BaseModel):
    total_files: int
    copied: int
    skipped: int
    missing: int
    errors: int
    total_bytes: int
    duration_ms: int


class CopyReport(BaseModel):
    summary: CopySummary
    files: list[CopyFileResult] = Field(default_factory=list)
