from fastapi import APIRouter

from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center

router = APIRouter()
repo = SheetsTaskRepository()


@router.get("/tasks/command-center")
def get_command_center():
    tasks = repo.get_command_center_tasks()
    return build_command_center(tasks)
