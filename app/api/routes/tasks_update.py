from fastapi import APIRouter, HTTPException
from app.schemas.update_schema import UpdateRequest, TaskBulkUpdateRequest, TaskBulkUpdateResponse
from app.repositories.sheets_status_log_repository import SheetsStatusLogRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()


def _get_repo():
    return SheetsTaskRepository()


def _get_status_log_repo():
    return SheetsStatusLogRepository()


def _normalize_status(status: str):
    return str(status or "").strip().casefold()


@router.post("/tasks/update")
def update_task(request: UpdateRequest):
    task = _get_repo().find_task_by_text(request.text)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    old_status = task.get("status", "")
    update_succeeded = _get_repo().update_task_status(task["task_id"], request.status)
    logged = False

    if update_succeeded and _normalize_status(old_status) != _normalize_status(request.status):
        _get_status_log_repo().create_log(task["task_id"], old_status, request.status)
        logged = True

    return {"updated": update_succeeded, "logged": logged}

@router.post("/tasks/bulk-update", response_model=TaskBulkUpdateResponse)
def bulk_update_tasks(request: TaskBulkUpdateRequest):
    updated_tasks, warnings = _get_repo().bulk_update_tasks(
        updates=[item.model_dump() for item in request.updates],
    )

    return TaskBulkUpdateResponse(
        updated_count=len(updated_tasks),
        updated_tasks=updated_tasks,
        warnings=warnings,
    )
