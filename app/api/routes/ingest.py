from fastapi import APIRouter, Query
from app.schemas.ingest_schema import IngestRequest
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.date_parser_service import parse_date_from_text, normalize_task_title
from app.services.priority_service import parse_priority_from_text
from app.services.category_service import classify_category
from app.services.task_parser_service import parse_tasks_from_text
from app.services.duplicate_detection_service import find_duplicate_task
from app.services.project_linking_service import resolve_project

router = APIRouter()
repo = SheetsTaskRepository()


def build_task_review(text: str, project: str = ""):
    existing_tasks = repo.sheet.get_all_records()
    review = parse_tasks_from_text(text)

    for task in review:
        task["project"] = resolve_project(
            task.get("raw_text", ""),
            project or "",
        )
        duplicate_result = find_duplicate_task(task, existing_tasks)
        task.update(duplicate_result)

    return review


@router.post("/ingest/review")
def review_tasks(request: IngestRequest):
    review = build_task_review(request.text, request.project)
    return {"review": review}


@router.get("/ingest/preview", operation_id="getTaskPreview")
def preview_tasks(
    text: str = Query(...),
    project: str = Query(""),
):
    review = build_task_review(text, project)
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
        project = resolve_project(task, request.project or "")

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
            project=project,
        )

        saved.append(task)

    return {"saved": saved}
