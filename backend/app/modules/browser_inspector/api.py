from fastapi import APIRouter

from .schemas import BrowserReport
from .service import scan

router = APIRouter(
    prefix="/browser",
    tags=["Browser Inspector"],
)


@router.get("", response_model=BrowserReport)
def browser():
    """Return the browser discovery report."""

    return scan()