from enum import StrEnum

from pydantic import BaseModel, Field

from app.modules.archive_engine.schemas import ArchiveReport
from app.modules.compression_engine.schemas import CompressionSettings
from app.modules.copy_engine.schemas import CopyReport
from app.modules.encryption_engine.schemas import EncryptionSettings
from app.modules.integrity_engine.schemas import IntegrityReport


class BackupSourceMode(StrEnum):
    WINDOWS_DISK = "windows_disk"
    CUSTOM_FOLDER = "custom_folder"


class BackupRunRequest(BaseModel):
    source_root: str = Field(min_length=1)
    source_mode: BackupSourceMode = BackupSourceMode.WINDOWS_DISK
    destination_directory: str = Field(min_length=1)
    archive_name: str = Field(min_length=1)
    selected_item_ids: list[str] | None = None
    compression: CompressionSettings = Field(default_factory=CompressionSettings)
    encryption: EncryptionSettings | None = None
    verify_integrity: bool = True


class BackupRunReport(BaseModel):
    success: bool
    archive_path: str | None = None
    copied_files: int = 0
    warnings: list[str] = Field(default_factory=list)
    error: str | None = None
    copy_report: CopyReport | None = None
    archive_report: ArchiveReport | None = None
    integrity_report: IntegrityReport | None = None
