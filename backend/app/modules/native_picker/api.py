from fastapi import APIRouter

from .schemas import (
    NativeOpenReport,
    NativeOpenRequest,
    NativePickerReport,
    NativePickerRequest,
)
from .service import NativePickerService

router = APIRouter(prefix="/system/picker", tags=["Native Picker"])


@router.post("/directory", response_model=NativePickerReport)
def pick_directory(request: NativePickerRequest) -> NativePickerReport:
    return NativePickerService.pick_directory(request.initial_path)


@router.post("/archive", response_model=NativePickerReport)
def pick_archive(request: NativePickerRequest) -> NativePickerReport:
    return NativePickerService.pick_archive(request.initial_path)


@router.post("/open", response_model=NativeOpenReport)
def open_location(request: NativeOpenRequest) -> NativeOpenReport:
    return NativePickerService.open_location(request.path)
