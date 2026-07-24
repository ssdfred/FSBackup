from fastapi import APIRouter

from .schemas import ArchiveReport, ArchiveRequest
from .service import ArchiveEngineService

router = APIRouter(
    prefix="/archive",
    tags=["Archive Engine"],
)


@router.post(
    "/create",
    response_model=ArchiveReport,
)
def create_archive(request: ArchiveRequest) -> ArchiveReport:
    return ArchiveEngineService.create(request)
