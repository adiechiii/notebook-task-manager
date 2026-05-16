import uuid
from datetime import datetime
from typing import Any

from app.services.capture_preview_service import classify_capture_type
from app.services.category_service import classify_category
from app.services.date_parser_service import normalize_task_title, parse_date_from_text
from app.services.duplicate_detection_service import find_duplicate_task
from app.services.memory_classification_service import classify_memory
from app.services.priority_service import parse_priority_from_text
from app.services.project_linking_service import resolve_project


CAPTURE_CONFIRMATION = "CONFIRM CAPTURE"
MEMORY_CAPTURE_TYPES = {"memory", "note", "idea", "reflection"}
UNSUPPORTED_CONFIRM_TYPES = {"expense_request", "recurring_task_request"}


def _clean(value: str) -> str:
    return str(value or "").strip()


def _normalized_type(value: str, text: str) -> str:
    cleaned = _clean(value).lower()
    if cleaned:
        return cleaned

    recommended_type, _, _ = classify_capture_type(text)
    return recommended_type


def _base_blocked_response(created_type: str, warning: str) -> dict[str, Any]:
    return {
        "confirmed": False,
        "created_type": created_type,
        "saved": {},
        "warnings": [warning],
    }


def _confirm_task(text: str, project: str, task_repo=None) -> dict[str, Any]:
    if task_repo is None:
        from app.repositories.sheets_task_repository import SheetsTaskRepository

        task_repo = SheetsTaskRepository()

    resolved_project = resolve_project(text, project or "")
    normalized_title = normalize_task_title(text)
    page_date = parse_date_from_text(text)
    priority = parse_priority_from_text(text)
    category = classify_category(text)

    duplicate_result = find_duplicate_task(
        {
            "raw_text": text,
            "normalized_title": normalized_title,
        },
        task_repo.sheet.get_all_records(),
    )

    duplicate_flag = "TRUE" if duplicate_result["duplicate"] else "FALSE"
    review_required = "TRUE" if duplicate_result["duplicate"] else "FALSE"

    task_id = task_repo.create_task(
        text=text,
        normalized_title=normalized_title,
        page_date=page_date,
        priority=priority,
        category=category,
        duplicate_flag=duplicate_flag,
        review_required=review_required,
        project=resolved_project,
    )

    warnings = []
    if duplicate_result["duplicate"]:
        warnings.append("Possible duplicate task was saved and marked for review.")

    return {
        "confirmed": True,
        "created_type": "task",
        "saved": {
            "task_id": task_id,
            "text": text,
            "normalized_title": normalized_title,
            "status": "Pending",
            "page_date": page_date,
            "priority": priority,
            "category": category,
            "project": resolved_project,
            "duplicate": duplicate_result["duplicate"],
        },
        "warnings": warnings,
    }


def _confirm_memory(text: str, project: str, created_type: str, memory_repo=None) -> dict[str, Any]:
    if memory_repo is None:
        from app.repositories.sheets_memory_repository import SheetsMemoryRepository

        memory_repo = SheetsMemoryRepository()

    resolved_project = resolve_project(text, project or "")
    classification = classify_memory(text)

    if resolved_project:
        classification["project"] = resolved_project

    if created_type in {"note", "idea", "reflection"}:
        classification["type"] = created_type.title()

    memory_id = memory_repo.create_memory(
        text,
        memory_type=classification["type"],
        entity=classification["entity"],
        project=classification["project"],
        tags=classification["tags"],
        importance=classification["importance"],
    )

    return {
        "confirmed": True,
        "created_type": created_type,
        "saved": {
            "memory_id": memory_id,
            "text": text,
            "classification": classification,
        },
        "warnings": [],
    }


def _decision_item(
    *,
    text: str,
    project: str,
    source_type: str,
    capture_source: str,
) -> dict[str, Any]:
    now = datetime.utcnow().isoformat()
    resolved_project = resolve_project(text, project or "")

    return {
        "decision_id": str(uuid.uuid4()),
        "decision": text,
        "context": "",
        "rationale": "",
        "outcome": "",
        "tradeoffs": "",
        "project": resolved_project,
        "tags": "",
        "status": "Active",
        "importance": parse_priority_from_text(text) or "Medium",
        "source_type": source_type or "text",
        "capture_source": capture_source or "manual",
        "created_at": now,
        "updated_at": now,
    }


def _confirm_decision(
    *,
    text: str,
    project: str,
    source_type: str,
    capture_source: str,
    decision_repo=None,
) -> dict[str, Any]:
    if decision_repo is None:
        from app.repositories.sheets_decision_repository import SheetsDecisionRepository

        decision_repo = SheetsDecisionRepository()

    inspection = decision_repo.inspect_schema()
    decision = _decision_item(
        text=text,
        project=project,
        source_type=source_type,
        capture_source=capture_source,
    )

    if not inspection["exists"] or inspection["headers_match"] is not True:
        warnings = list(inspection["warnings"])
        warnings.append("Decision was not saved because the Decisions schema is not ready.")
        return {
            "confirmed": False,
            "created_type": "decision",
            "saved": {},
            "warnings": warnings,
        }

    duplicate_candidates = decision_repo.find_duplicate_candidates(
        decision["decision"],
        decision["project"],
    )

    warnings = []
    if duplicate_candidates:
        warnings.append("Possible duplicate decision found. Decision was saved anyway.")

    result = decision_repo.create_decision(decision)
    warnings.extend(result["warnings"])

    return {
        "confirmed": result["created"],
        "created_type": "decision",
        "saved": {
            "decision": result["decision"],
            "schema_ok": result["schema_ok"],
            "duplicate_candidates": duplicate_candidates,
        },
        "warnings": warnings,
    }


def confirm_capture(
    *,
    text: str,
    project: str = "",
    recommended_type: str = "",
    source_type: str = "text",
    capture_source: str = "manual",
    confirmation: str = "",
    task_repo=None,
    memory_repo=None,
    decision_repo=None,
) -> dict[str, Any]:
    cleaned_text = _clean(text)
    created_type = _normalized_type(recommended_type, cleaned_text)

    if confirmation != CAPTURE_CONFIRMATION:
        return _base_blocked_response(
            created_type,
            "Exact confirmation phrase is required. No capture was saved.",
        )

    if not cleaned_text:
        return _base_blocked_response(
            created_type,
            "Text is empty. No capture was saved.",
        )

    if created_type == "task":
        return _confirm_task(cleaned_text, project, task_repo=task_repo)

    if created_type in MEMORY_CAPTURE_TYPES:
        return _confirm_memory(
            cleaned_text,
            project,
            created_type,
            memory_repo=memory_repo,
        )

    if created_type == "decision":
        return _confirm_decision(
            text=cleaned_text,
            project=project,
            source_type=source_type,
            capture_source=capture_source,
            decision_repo=decision_repo,
        )

    if created_type in UNSUPPORTED_CONFIRM_TYPES:
        return _base_blocked_response(
            created_type,
            f"{created_type} is preview-only right now. No capture was saved.",
        )

    return _base_blocked_response(
        created_type,
        f"Unsupported capture type: {created_type}. No capture was saved.",
    )
