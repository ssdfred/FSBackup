from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, Field

from app.modules.execution_planner.schemas import ExecutionPlan


class CopyStatus(StrEnum):
    COPIED = "copied"
    SKIPPED = "skipped"
    MISSING = "missing"
    ERROR = "error"


class CopyIssueSeverity(StrEnum):
    WARNING = "warning"
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
    winerror: int | None = None


class CopyIssue(BaseModel):
    severity: CopyIssueSeverity
    code: str
    message: str
    source: str | None = None
    destination: str | None = None


class CopySummary(BaseModel):
    total_files: int
    copied: int
    skipped: int
    missing: int
    errors: int
    total_bytes: int
    duration_ms: int


class CopyReport(BaseModel):
    execution_id: UUID
    started_at: datetime
    finished_at: datetime
    duration_ms: int
    success: bool
    summary: CopySummary
    files: list[CopyFileResult] = Field(default_factory=list)
    warnings: list[CopyIssue] = Field(default_factory=list)
    errors: list[CopyIssue] = Field(default_factory=list)
    metadata: dict[str, str | int | bool] = Field(default_factory=dict)
