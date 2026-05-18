from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.repositories.sheets_status_log_repository import SheetsStatusLogRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.schemas.archive_schema import ArchiveRequest

router = APIRouter()


def _get_repo():
    return SheetsTaskRepository()


def _get_status_log_repo():
    return SheetsStatusLogRepository()

ARCHIVE_CONFIRMATION = "ARCHIVE COMPLETED TASKS"
ARCHIVABLE_STATUSES = {"done", "completed"}


@router.get("/tasks/archive-preview")
def get_archive_preview(
    status: str = Query(default="Done"),
    older_than_days: int = Query(default=0, ge=0),
    include_done: bool = Query(default=True),
):
    candidates = _get_repo().get_archive_preview_candidates(
        status=status,
        older_than_days=older_than_days,
        include_done=include_done,
    )

    warnings = []
    if not candidates:
        warnings.append("No archive candidates found.")

    return {
        "dry_run": True,
        "candidate_count": len(candidates),
        "criteria": {
            "status": status,
            "older_than_days": older_than_days,
            "include_done": include_done,
        },
        "candidates": candidates,
        "warnings": warnings,
    }


@router.post("/tasks/archive")
def archive_tasks(request: ArchiveRequest):
    criteria = {
        "status": request.status,
        "older_than_days": request.older_than_days,
        "include_done": request.include_done,
    }

    if request.confirm != ARCHIVE_CONFIRMATION:
        return JSONResponse(
            status_code=400,
            content={
                "dry_run": False,
                "archived_count": 0,
                "criteria": criteria,
                "archived": [],
                "warnings": ["Exact confirmation phrase is required. No tasks were archived."],
            },
        )

    requested_status = str(request.status or "").strip().lower()
    if requested_status not in ARCHIVABLE_STATUSES:
        return JSONResponse(
            status_code=400,
            content={
                "dry_run": False,
                "archived_count": 0,
                "criteria": criteria,
                "archived": [],
                "warnings": ["Only Done or Completed tasks can be archived. No tasks were archived."],
            },
        )

    if request.older_than_days < 0:
        return JSONResponse(
            status_code=400,
            content={
                "dry_run": False,
                "archived_count": 0,
                "criteria": criteria,
                "archived": [],
                "warnings": ["older_than_days must be greater than or equal to 0. No tasks were archived."],
            },
        )

    archived, warnings = _get_repo().archive_tasks(
        status=request.status,
        older_than_days=request.older_than_days,
        include_done=request.include_done,
    )

    if not archived:
        warnings.append("No archive candidates found.")

    logged_count = 0
    for task in archived:
        _get_status_log_repo().create_log(
            task.get("task_id"),
            task.get("previous_status"),
            "Archived",
            change_source="archive",
        )
        logged_count += 1

    return {
        "dry_run": False,
        "archived_count": len(archived),
        "criteria": criteria,
        "archived": archived,
        "warnings": warnings,
        "logged_count": logged_count,
    }
