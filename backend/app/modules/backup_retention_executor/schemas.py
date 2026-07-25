from pydantic import BaseModel, Field

from app.modules.backup_retention.schemas import RetentionSimulationReport


class RetentionExecutionRequest(BaseModel):
    simulation: RetentionSimulationReport
    confirmation: str = Field(min_length=1)


class RetentionFileResult(BaseModel):
    path: str
    deleted: bool
    size_bytes: int = Field(ge=0)
    error: str | None = None


class RetentionExecutionSummary(BaseModel):
    requested: int = Field(ge=0)
    deleted: int = Field(ge=0)
    failed: int = Field(ge=0)
    reclaimed_bytes: int = Field(ge=0)


class RetentionExecutionReport(BaseModel):
    success: bool
    confirmed: bool
    files: list[RetentionFileResult] = Field(default_factory=list)
    summary: RetentionExecutionSummary
    error: str | None = None
