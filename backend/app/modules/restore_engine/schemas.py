from pydantic import BaseModel


class RestoreRequest(BaseModel):
    archive_path: str
    destination_directory: str
    overwrite: bool = False


class RestoreReport(BaseModel):
    archive_path: str
    destination_directory: str
    restored_files: int
    skipped_files: int
    duration_ms: int
    success: bool
    error: str | None = None
