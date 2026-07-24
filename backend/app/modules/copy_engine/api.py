from fastapi import APIRouter

from .schemas import CopyReport, CopyRequest
from .service import CopyEngineService

router = APIRouter(
    prefix="/copy",
    tags=["Copy Engine"],
)


@router.post(
    "/execute",
    response_model=CopyReport,
)
def execute_copy(request: CopyRequest) -> CopyReport:
    return CopyEngineService.execute(request)