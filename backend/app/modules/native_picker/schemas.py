from pydantic import BaseModel, Field


class NativePickerRequest(BaseModel):
    initial_path: str | None = None


class NativePickerReport(BaseModel):
    selected: bool
    path: str | None = None
    error: str | None = None


class NativeOpenRequest(BaseModel):
    path: str = Field(min_length=1)


class NativeOpenReport(BaseModel):
    success: bool
    error: str | None = None
