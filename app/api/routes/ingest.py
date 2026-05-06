from fastapi import APIRouter
from app.schemas.ingest_schema import IngestRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.date_parser_service import parse_date_from_text, normalize_task_title
from app.services.priority_service import parse_priority_from_text
from app.services.category_service import classify_category
from app.services.task_parser_service import parse_tasks_from_text

router = APIRouter()
repo = SheetsTaskRepository()


@router.post("/ingest/review")
def review_tasks(request: IngestRequest):
    review = parse_tasks_from_text(request.text)
    return {"review": review}


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
        priority = parse_priority_from_text(task)
        category = classify_category(task)

        repo.create_task(
            text=task,
            normalized_title=normalized_title,
            page_date=page_date,
            priority=priority,
            category=category,
        )

        saved.append(task)

    return {"saved": saved}