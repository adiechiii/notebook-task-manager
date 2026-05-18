from fastapi import APIRouter, Query
from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()


def _get_repo():
    return SheetsTaskRepository()


@router.get("/tasks")
def get_tasks(status: str = Query(default=None)):
    tasks = _get_repo().get_all_tasks(status)
    return {"tasks": tasks}