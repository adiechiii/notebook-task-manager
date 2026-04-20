from fastapi import APIRouter, Query
from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()
repo = SheetsTaskRepository()


@router.get("/tasks")
def get_tasks(status: str = Query(default=None)):
    tasks = repo.get_all_tasks(status)
    return {"tasks": tasks}