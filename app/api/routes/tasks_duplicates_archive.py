from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.services.duplicate_cleanup_archive_service import (
    DUPLICATE_ARCHIVE_CONFIRMATION,
    archive_duplicate_cleanup_candidates,
)


router = APIRouter()


class DuplicateArchiveRequest(BaseModel):
    task_ids: list[str] = Field(default_factory=list)
    dry_run: bool = True
    confirmation: str = ""


@router.post("/tasks/duplicates/archive")
def archive_duplicate_tasks(request: DuplicateArchiveRequest):
    result = archive_duplicate_cleanup_candidates(
        task_ids=request.task_ids,
        dry_run=request.dry_run,
        confirmation=request.confirmation,
    )

    if not request.dry_run and request.confirmation != DUPLICATE_ARCHIVE_CONFIRMATION:
        return JSONResponse(status_code=400, content=result)

    return result
