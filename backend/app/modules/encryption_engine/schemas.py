from pydantic import BaseModel, Field, SecretStr


class EncryptionSettings(BaseModel):
    password: SecretStr
    associated_data: str = "FSBackup:FSBE:1"


class EncryptionReport(BaseModel):
    source_path: str
    destination_path: str
    input_size: int = 0
    output_size: int = 0
    duration_ms: int
    success: bool
    error: str | None = None


class DecryptionSettings(BaseModel):
    password: SecretStr
    associated_data: str = "FSBackup:FSBE:1"
    overwrite: bool = Field(default=False)
