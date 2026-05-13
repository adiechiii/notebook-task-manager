from datetime import datetime

from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center

FOCUS_LIMIT = 3


def _display_text(value):
    return str(value or "").strip()


def _is_priority(task, priority):
    return _display_text(task.get("priority")).lower() == priority


def _task_key(task):
    return (
        _display_text(task.get("title") or task.get("text")).lower(),
        _display_text(task.get("status")).lower(),
        _display_text(task.get("page_date")),
        _display_text(task.get("category")).lower(),
        _display_text(task.get("priority")).lower(),
        _display_text(task.get("project")).lower(),
    )


def _slim_task(task):
    return {
        "title": task.get("title") or task.get("text"),
        "status": task.get("status"),
        "page_date": task.get("page_date"),
        "category": task.get("category"),
        "priority": task.get("priority"),
        "project": task.get("project"),
    }


def _ranked_focus_candidates(command_center):
    ranked_groups = [
        [
            task
            for task in command_center.get("overdue", [])
            if _is_priority(task, "high")
        ],
        [
            task
            for task in command_center.get("overdue", [])
            if _is_priority(task, "medium")
        ],
        [
            task
            for task in command_center.get("today", [])
            if _is_priority(task, "high")
        ],
        [
            task
            for task in command_center.get("today", [])
            if _is_priority(task, "medium")
        ],
        [
            task
            for task in command_center.get("no_date", [])
            if _is_priority(task, "high")
        ],
        command_center.get("overdue", []),
        command_center.get("today", []),
        command_center.get("no_date", []),
    ]

    candidates = []
    seen = set()

    for group in ranked_groups:
        for task in group:
            key = _task_key(task)
            if key in seen:
                continue

            seen.add(key)
            candidates.append(task)

    return candidates


def _counts(command_center, focus_candidates, selected):
    return {
        "today": len(command_center.get("today", [])),
        "overdue": len(command_center.get("overdue", [])),
        "upcoming": len(command_center.get("upcoming", [])),
        "no_date": len(command_center.get("no_date", [])),
        "done": len(command_center.get("done", [])),
        "focus_candidates": len(focus_candidates),
        "selected": len(selected),
    }


def _ignored_for_focus(command_center, focus_candidates, selected):
    return {
        "upcoming": len(command_center.get("upcoming", [])),
        "done": len(command_center.get("done", [])),
        "not_selected_active": max(len(focus_candidates) - len(selected), 0),
    }


def _warnings(focus_candidates, selected):
    if not focus_candidates:
        return ["No active overdue, today, or no-date tasks found."]

    if len(selected) < FOCUS_LIMIT:
        return ["Fewer than 3 focus tasks are available."]

    return []


def build_focus_mode(task_repo=None):
    task_repo = task_repo or SheetsTaskRepository()

    tasks = task_repo.get_command_center_tasks()
    command_center = build_command_center(tasks)
    focus_candidates = _ranked_focus_candidates(command_center)
    selected = focus_candidates[:FOCUS_LIMIT]

    return {
        "date": datetime.utcnow().date().isoformat(),
        "mode": "focus",
        "focus_statement": "Focus on the top 3 active tasks.",
        "top_3": [_slim_task(task) for task in selected],
        "counts": _counts(command_center, focus_candidates, selected),
        "ignored_for_focus": _ignored_for_focus(
            command_center,
            focus_candidates,
            selected,
        ),
        "warnings": _warnings(focus_candidates, selected),
    }
