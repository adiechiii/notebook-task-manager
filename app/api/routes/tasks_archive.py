from fastapi import APIRouter, Query

from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()
repo = SheetsTaskRepository()


@router.get("/tasks/archive-preview")
def get_archive_preview(
    status: str = Query(default="Done"),
    older_than_days: int = Query(default=0, ge=0),
    include_done: bool = Query(default=True),
):
    candidates = repo.get_archive_preview_candidates(
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
