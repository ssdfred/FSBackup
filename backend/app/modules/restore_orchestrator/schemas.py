from pydantic import BaseModel, Field, SecretStr

from app.modules.integrity_engine.schemas import IntegrityReport
from app.modules.restore_engine.schemas import RestoreReport


class RestoreRunRequest(BaseModel):
    archive_path: str
    destination_directory: str
    overwrite: bool = False
    password: SecretStr | None = None


class RestoreRunReport(BaseModel):
    archive_path: str
    destination_directory: str
    integrity_report: IntegrityReport
    restore_report: RestoreReport | None = None
    success: bool
    error: str | None = None
    archive_paths: list[str] = Field(default_factory=list)
    total_segments: int = 0
    restored_segments: int = 0
