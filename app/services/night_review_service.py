from datetime import datetime

from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center
from app.services.project_rollup_service import build_project_rollups

COMPACT_LIMIT = 5
PRIORITY_ORDER = {
    "high": 0,
    "medium": 1,
    "low": 2,
}


def _display_text(value):
    return str(value or "").strip()


def _priority_rank(task):
    return PRIORITY_ORDER.get(_display_text(task.get("priority")).lower(), 3)


def _parse_date(value):
    text = _display_text(value)
    if not text:
        return None

    try:
        return datetime.fromisoformat(text).date()
    except ValueError:
        return None


def _slim_task(task):
    return {
        "title": task.get("title") or task.get("text"),
        "status": task.get("status"),
        "page_date": task.get("page_date"),
        "category": task.get("category"),
        "priority": task.get("priority"),
        "project": task.get("project"),
    }


def _slim_memory(memory):
    return {
        "summary": memory.get("Memory Summary") or memory.get("summary") or memory.get("Raw Text"),
        "type": memory.get("Memory Type") or memory.get("type"),
        "entity": memory.get("Entity") or memory.get("entity"),
        "project": memory.get("Project") or memory.get("project"),
        "tags": memory.get("Tags") or memory.get("tags"),
        "importance": memory.get("Importance") or memory.get("importance"),
        "created_at": memory.get("Created At") or memory.get("created_at"),
    }


def _limited_tasks(tasks, limit=COMPACT_LIMIT):
    sorted_tasks = sorted(tasks or [], key=_priority_rank)
    return [_slim_task(task) for task in sorted_tasks[:limit]]


def _completed_tasks(command_center):
    return [_slim_task(task) for task in command_center.get("done", [])[:COMPACT_LIMIT]]


def _remaining_tasks(command_center):
    remaining = []

    for bucket in ("overdue", "today", "no_date", "upcoming"):
        remaining.extend(command_center.get(bucket, []))

    return _limited_tasks(remaining)


def _today_memory_rows(memory_repo):
    today = datetime.utcnow().date()
    memories = []

    for row in memory_repo.sheet.get_all_records():
        created_date = _parse_date(row.get("Created At"))
        if created_date == today:
            memories.append(_slim_memory(row))

    return memories[:COMPACT_LIMIT]


def _project_progress(project_rollups):
    if not project_rollups:
        return {}

    return {
        "total_projects": project_rollups.get("total_projects", 0),
        "active_projects": project_rollups.get("active_projects", 0),
        "items": (project_rollups.get("items") or [])[:COMPACT_LIMIT],
        "active_projects_without_links": (
            project_rollups.get("active_projects_without_links") or []
        )[:COMPACT_LIMIT],
    }


def _suggested_tomorrow_carryover(command_center):
    carryover = []

    for bucket in ("overdue", "today"):
        carryover.extend(command_center.get(bucket, []))

    carryover.extend(
        task
        for task in command_center.get("no_date", [])
        if _display_text(task.get("priority")).lower() == "high"
    )

    return _limited_tasks(carryover)


def _summary(command_center, memories_captured_today):
    overdue_count = len(command_center.get("overdue", []))
    remaining_count = (
        overdue_count
        + len(command_center.get("today", []))
        + len(command_center.get("no_date", []))
        + len(command_center.get("upcoming", []))
    )
    done_count = len(command_center.get("done", []))

    return {
        "completed_visible": done_count,
        "remaining": remaining_count,
        "overdue_remaining": overdue_count,
        "memories_captured_today": len(memories_captured_today),
    }


def _warnings(project_rollups):
    warnings = [
        "Archived/completed history is limited until StatusLog read support is added."
    ]

    if project_rollups.get("unlinked_tasks", 0):
        warnings.append("Some tasks are not linked to a project.")

    if project_rollups.get("unmatched_project_tasks", 0) or project_rollups.get(
        "unmatched_project_memories", 0
    ):
        warnings.append("Some linked project names do not match a project record.")

    return warnings


def build_night_review(
    task_repo=None,
    memory_repo=None,
    project_repo=None,
):
    task_repo = task_repo or SheetsTaskRepository()
    memory_repo = memory_repo or SheetsMemoryRepository()
    project_repo = project_repo or SheetsProjectRepository()

    tasks = task_repo.get_command_center_tasks()
    command_center = build_command_center(tasks)
    memories = memory_repo.search_memories("")
    projects = project_repo.search_projects("")
    project_rollups = build_project_rollups(tasks, memories, projects, command_center)
    memories_captured_today = _today_memory_rows(memory_repo)

    return {
        "date": datetime.utcnow().date().isoformat(),
        "summary": _summary(command_center, memories_captured_today),
        "completed_tasks": _completed_tasks(command_center),
        "remaining_tasks": _remaining_tasks(command_center),
        "archived_or_done_summary": {
            "visible_done_count": len(command_center.get("done", [])),
            "archived_count": None,
            "history_limited": True,
        },
        "memories_captured_today": memories_captured_today,
        "project_progress": _project_progress(project_rollups),
        "suggested_tomorrow_carryover": _suggested_tomorrow_carryover(command_center),
        "warnings": _warnings(project_rollups),
    }
