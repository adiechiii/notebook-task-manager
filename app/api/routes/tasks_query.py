from fastapi import APIRouter
from app.api.schemas.query_schema import QueryRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()
repo = SheetsTaskRepository()


@router.post("/query")
def query_tasks(request: QueryRequest):

    filters = {}

    if request.status:
        filters["Status"] = request.status

    if request.category:
        filters["Category"] = request.category

    if request.date:
        filters["Capture Date"] = request.date

    if not filters:
        tasks = repo.get_all_tasks()
    else:
        tasks = repo.filter_tasks(filters)

    return {
        "tasks": tasks,
        "count": len(tasks)
    }