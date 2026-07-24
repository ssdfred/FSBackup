from fastapi import APIRouter

from .schemas import IntegrityReport, IntegrityRequest
from .service import IntegrityEngineService

router = APIRouter(prefix="/integrity", tags=["Integrity Engine"])


@router.post("/verify", response_model=IntegrityReport)
def verify_archive(request: IntegrityRequest) -> IntegrityReport:
    return IntegrityEngineService.verify(request)
