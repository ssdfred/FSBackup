from pydantic import BaseModel


class NativePickerRequest(BaseModel):
    initial_path: str | None = None


class NativePickerReport(BaseModel):
    selected: bool
    path: str | None = None
    error: str | None = None
