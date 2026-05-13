import re
from collections import defaultdict
from datetime import datetime

from app.repositories.sheets_task_repository import SheetsTaskRepository


PUNCTUATION_NOISE = re.compile(r"[^\w\s]", re.ASCII)
WHITESPACE = re.compile(r"\s+")
PRIORITY_RANK = {
    "high": 3,
    "medium": 2,
    "low": 1,
    "": 0,
}
WARNINGS = [
    "Dry-run only. No tasks were changed.",
    "Suggested archive candidates are recommendations only.",
    "Similar task titles may include legitimate recurring tasks.",
]


def _display_value(value):
    return str(value or "").strip()


def _normalize_title(task):
    value = task.get("title") or task.get("text") or ""
    value = PUNCTUATION_NOISE.sub(" ", str(value).casefold().strip())
    return WHITESPACE.sub(" ", value).strip()


def _compact_task(task):
    return {
        "task_id": task.get("task_id"),
        "text": task.get("text"),
        "title": task.get("title"),
        "status": task.get("status"),
        "page_date": task.get("page_date"),
        "category": task.get("category"),
        "priority": task.get("priority"),
        "project": task.get("project"),
        "created_at": task.get("created_at"),
        "updated_at": task.get("updated_at"),
        "duplicate_flag": task.get("duplicate_flag"),
        "review_required": task.get("review_required"),
    }


def _same_value(candidates, key, casefold=False):
    values = set()

    for task in candidates:
        value = _display_value(task.get(key))
        if casefold:
            value = value.casefold()
        values.add(value)

    return len(values) == 1


def _confidence(candidates):
    same_page_date = _same_value(candidates, "page_date")
    same_project = _same_value(candidates, "project", casefold=True)

    if same_page_date and same_project:
        return (
            "high",
            "same_normalized_title_page_date_project",
        )

    if same_project:
        return (
            "medium",
            "same_normalized_title_project_with_different_or_blank_dates",
        )

    return (
        "low",
        "same_normalized_title_only_with_different_dates_or_projects",
    )


def _priority_score(task):
    return PRIORITY_RANK.get(_display_value(task.get("priority")).casefold(), 0)


def _created_at_sort_value(task):
    value = _display_value(task.get("created_at"))
    if not value:
        return datetime.max

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return datetime.max


def _richness_score(task):
    return len(_display_value(task.get("text"))) + len(_display_value(task.get("title")))


def _keep_sort_key(task):
    return (
        0 if _display_value(task.get("project")) else 1,
        0 if _display_value(task.get("page_date")) else 1,
        -_priority_score(task),
        _created_at_sort_value(task),
        -_richness_score(task),
    )


def _suggested_keep(candidates):
    chosen = min(candidates, key=_keep_sort_key)
    return {
        "candidate": _compact_task(chosen),
        "reason": (
            "Informational only. Prefers non-blank project, dated tasks, "
            "higher priority, earliest created_at, then richer text/title."
        ),
    }


def _group_key(normalized_title):
    return f"normalized_title:{normalized_title}"


def build_duplicate_cleanup_plan(task_repo=None):
    task_repo = task_repo or SheetsTaskRepository()
    tasks = task_repo.get_active_tasks_for_duplicate_cleanup()

    groups_by_title = defaultdict(list)

    for task in tasks:
        if _display_value(task.get("status")).casefold() == "archived":
            continue

        normalized_title = _normalize_title(task)
        if not normalized_title:
            continue

        groups_by_title[normalized_title].append(task)

    cleanup_plan = []

    for normalized_title in sorted(groups_by_title):
        candidates = groups_by_title[normalized_title]
        if len(candidates) < 2:
            continue

        confidence, reason = _confidence(candidates)
        suggested_keep = _suggested_keep(candidates)
        keep_task_id = suggested_keep["candidate"].get("task_id")

        cleanup_plan.append({
            "group_key": _group_key(normalized_title),
            "confidence": confidence,
            "reason": reason,
            "suggested_keep": suggested_keep,
            "suggested_archive": [
                _compact_task(task)
                for task in candidates
                if task.get("task_id") != keep_task_id
            ],
            "candidates": [_compact_task(task) for task in candidates],
        })

    return {
        "dry_run": True,
        "cleanup_plan": cleanup_plan,
        "summary": {
            "groups": len(cleanup_plan),
            "suggested_archive_count": sum(
                len(group["suggested_archive"]) for group in cleanup_plan
            ),
            "candidate_tasks": sum(
                len(group["candidates"]) for group in cleanup_plan
            ),
        },
        "warnings": WARNINGS.copy(),
    }
