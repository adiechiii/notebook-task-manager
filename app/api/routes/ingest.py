from fastapi import APIRouter
from app.schemas.ingest_schema import IngestRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.date_parser_service import parse_date_from_text, normalize_task_title

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

        page_date = parse_date_from_text(task)
        normalized_title = normalize_task_title(task)

        repo.create_task(
            text=task,
            normalized_title=normalized_title,
            page_date=page_date,
        )

        saved.append(task)

    return {"saved": saved}