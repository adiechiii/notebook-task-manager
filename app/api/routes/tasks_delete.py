from fastapi import APIRouter, HTTPException
from app.schemas.delete_schema import DeleteRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()
repo = SheetsTaskRepository()


@router.post("/tasks/delete")
def delete_task(request: DeleteRequest):
    task = repo.find_task_by_text(request.text)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    repo.delete_task(task["task_id"])

    return {"deleted": True}