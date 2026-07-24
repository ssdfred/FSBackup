from fastapi import APIRouter

from .schemas import RestoreReport, RestoreRequest
from .service import RestoreEngineService

router = APIRouter(
    prefix="/restore",
    tags=["Restore Engine"],
)


@router.post(
    "/execute",
    response_model=RestoreReport,
)
def execute_restore(request: RestoreRequest) -> RestoreReport:
    return RestoreEngineService.restore(request)
