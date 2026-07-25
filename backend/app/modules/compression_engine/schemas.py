from enum import StrEnum

from pydantic import BaseModel, Field


class CompressionMethod(StrEnum):
    STORED = "stored"
    DEFLATED = "deflated"


class CompressionSettings(BaseModel):
    method: CompressionMethod = CompressionMethod.DEFLATED
    level: int = Field(default=6, ge=0, le=9)


class CompressionMetrics(BaseModel):
    method: CompressionMethod
    level: int
    original_size: int
    compressed_size: int
    saved_bytes: int
    ratio: float
