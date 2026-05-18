from fastapi import APIRouter, HTTPException
from app.schemas.delete_schema import DeleteRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()


def _get_repo():
    return SheetsTaskRepository()


@router.post("/tasks/delete")
def delete_task(request: DeleteRequest):
    task = _get_repo().find_task_by_text(request.text)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    _get_repo().delete_task(task["task_id"])

    return {"deleted": True}