from fastapi import APIRouter, HTTPException
from app.schemas.update_schema import UpdateRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()
repo = SheetsTaskRepository()


@router.post("/tasks/update")
def update_task(request: UpdateRequest):
    task = repo.find_task_by_text(request.text)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    repo.update_task_status(task["task_id"], request.status)

    return {"updated": True}