from pydantic import BaseModel, Field


class UiCapability(BaseModel):
    key: str
    label: str
    endpoint: str
    method: str
    destructive: bool = False


class UiDashboardSummary(BaseModel):
    application: str = "FSBackup"
    api_version: str
    status: str = "ready"
    capabilities: list[UiCapability] = Field(default_factory=list)
