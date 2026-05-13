import re
from collections import defaultdict

from app.repositories.sheets_task_repository import SheetsTaskRepository


PUNCTUATION_NOISE = re.compile(r"[^\w\s]", re.ASCII)
WHITESPACE = re.compile(r"\s+")


def _normalize_title(task):
    value = task.get("title") or task.get("text") or ""
    value = PUNCTUATION_NOISE.sub(" ", str(value).casefold().strip())
    return WHITESPACE.sub(" ", value).strip()


def _compact_task(task):
    return {
        "text": task.get("text"),
        "title": task.get("title"),
        "status": task.get("status"),
        "page_date": task.get("page_date"),
        "category": task.get("category"),
        "priority": task.get("priority"),
        "project": task.get("project"),
    }


def _display_value(value):
    return str(value or "").strip()


def _reason(normalized_title, candidates):
    page_dates = {_display_value(task.get("page_date")) for task in candidates}
    projects = {_display_value(task.get("project")).casefold() for task in candidates}

    if len(page_dates) == 1 and len(projects) == 1:
        return "same_normalized_title_page_date_project"

    if len(projects) == 1:
        return "same_normalized_title_project"

    return "same_normalized_title"


def _created_at_value(task):
    return _display_value(task.get("created_at") or task.get("createdAt"))


def _suggested_keep(candidates):
    chosen = candidates[0]
    dated_candidates = [task for task in candidates if _created_at_value(task)]

    if dated_candidates:
        chosen = min(dated_candidates, key=_created_at_value)

    return {
        "candidate": _compact_task(chosen),
        "reason": "Informational only. No cleanup is performed; earliest created_at is preferred when available, otherwise the first candidate is shown.",
    }


def _group_key(normalized_title):
    return f"normalized_title:{normalized_title}"


def build_duplicate_tasks_preview(task_repo=None):
    task_repo = task_repo or SheetsTaskRepository()
    tasks = task_repo.get_command_center_tasks()

    groups_by_title = defaultdict(list)
    warnings = []

    for task in tasks:
        if _display_value(task.get("status")).casefold() == "archived":
            continue

        normalized_title = _normalize_title(task)
        if not normalized_title:
            continue

        groups_by_title[normalized_title].append(task)

    duplicate_groups = []

    for normalized_title in sorted(groups_by_title):
        candidates = groups_by_title[normalized_title]
        if len(candidates) < 2:
            continue

        duplicate_groups.append({
            "group_key": _group_key(normalized_title),
            "count": len(candidates),
            "reason": _reason(normalized_title, candidates),
            "suggested_keep": _suggested_keep(candidates),
            "candidates": [_compact_task(task) for task in candidates],
        })

    if duplicate_groups:
        warnings.append("Preview only. Similar task titles may include legitimate recurring tasks.")

    if any("task_id" not in task and "Task ID" not in task for task in tasks):
        warnings.append("Task IDs are unavailable; preview is based on visible task fields only.")

    return {
        "dry_run": True,
        "duplicate_groups": duplicate_groups,
        "summary": {
            "groups": len(duplicate_groups),
            "candidate_tasks": sum(group["count"] for group in duplicate_groups),
        },
        "warnings": warnings,
    }
