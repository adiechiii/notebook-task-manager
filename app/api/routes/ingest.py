from fastapi import APIRouter
from app.schemas.ingest_schema import IngestRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository

router = APIRouter()
repo = SheetsTaskRepository()


@router.post("/ingest/confirm")
def confirm_tasks(request: IngestRequest):
    lines = request.text.split("\n")

    saved = []

    for line in lines:
        task = line.strip()
        if not task:
            continue

        repo.create_task(task)
        saved.append(task)

    return {"saved": saved}