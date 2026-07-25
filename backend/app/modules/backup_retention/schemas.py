from enum import StrEnum

from pydantic import BaseModel, Field

from app.modules.backup_catalog.schemas import BackupCatalogReport


class RetentionDecision(StrEnum):
    KEEP = "keep"
    DELETE = "delete"
    PROTECT = "protect"


class RetentionPolicy(BaseModel):
    keep_last: int = Field(default=3, ge=0, le=1000)
    keep_daily_days: int = Field(default=7, ge=0, le=3650)
    keep_weekly_weeks: int = Field(default=4, ge=0, le=520)
    keep_monthly_months: int = Field(default=12, ge=0, le=1200)


class RetentionSimulationRequest(BaseModel):
    catalog: BackupCatalogReport
    policy: RetentionPolicy = Field(default_factory=RetentionPolicy)


class RetentionArchiveDecision(BaseModel):
    path: str
    name: str
    decision: RetentionDecision
    reason: str
    size_bytes: int = Field(ge=0)


class RetentionSimulationSummary(BaseModel):
    total: int = Field(ge=0)
    keep: int = Field(ge=0)
    delete: int = Field(ge=0)
    protect: int = Field(ge=0)
    reclaimable_bytes: int = Field(ge=0)


class RetentionSimulationReport(BaseModel):
    decisions: list[RetentionArchiveDecision] = Field(default_factory=list)
    summary: RetentionSimulationSummary
    simulated: bool = True
