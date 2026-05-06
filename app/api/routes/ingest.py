from fastapi import APIRouter
from app.schemas.ingest_schema import IngestRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.date_parser_service import parse_date_from_text, normalize_task_title
from app.services.priority_service import parse_priority_from_text
from app.services.category_service import classify_category
from app.services.task_parser_service import parse_tasks_from_text
from app.services.duplicate_detection_service import find_duplicate_task

router = APIRouter()
repo = SheetsTaskRepository()


@router.post("/ingest/review")
def review_tasks(request: IngestRequest):
    existing_tasks = repo.sheet.get_all_records()
    review = parse_tasks_from_text(request.text)

    for task in review:
        duplicate_result = find_duplicate_task(task, existing_tasks)
        task.update(duplicate_result)

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

        duplicate_result = find_duplicate_task(
            {
                "raw_text": task,
                "normalized_title": normalized_title,
            },
            repo.sheet.get_all_records(),
        )

        duplicate_flag = "TRUE" if duplicate_result["duplicate"] else "FALSE"
        review_required = "TRUE" if duplicate_result["duplicate"] else "FALSE"

        repo.create_task(
            text=task,
            normalized_title=normalized_title,
            page_date=page_date,
            priority=priority,
            category=category,
            duplicate_flag=duplicate_flag,
            review_required=review_required,
        )

        saved.append(task)

    return {"saved": saved}