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


def _slim_task(task):
    return {
        "title": task.get("title") or task.get("text"),
        "status": task.get("status"),
        "page_date": task.get("page_date"),
        "category": task.get("category"),
        "priority": task.get("priority"),
        "project": task.get("project"),
    }


def _limited_tasks(tasks, limit=COMPACT_LIMIT):
    sorted_tasks = sorted(tasks or [], key=_priority_rank)
    return [_slim_task(task) for task in sorted_tasks[:limit]]


def _active_projects(projects):
    return [
        project
        for project in projects or []
        if _display_text(project.get("status")).lower() == "active"
    ]


def _counts(command_center, memories, projects):
    active_projects = _active_projects(projects)
    return {
        "today": len(command_center.get("today", [])),
        "overdue": len(command_center.get("overdue", [])),
        "upcoming": len(command_center.get("upcoming", [])),
        "no_date": len(command_center.get("no_date", [])),
        "done": len(command_center.get("done", [])),
        "memories": len(memories or []),
        "active_projects": len(active_projects),
    }


def _focus(counts):
    parts = []

    if counts["overdue"]:
        parts.append(f"{counts['overdue']} overdue task(s)")

    if counts["today"]:
        parts.append(f"{counts['today']} task(s) due today")

    if counts["no_date"]:
        parts.append(f"{counts['no_date']} task(s) without dates")

    if not parts:
        return "No urgent dated tasks are waiting right now."

    return "Start with " + ", ".join(parts) + "."


def _top_priorities(command_center):
    candidates = []

    for bucket in ("overdue", "today", "no_date", "upcoming"):
        candidates.extend(command_center.get(bucket, []))

    candidates = [
        task
        for task in candidates
        if _display_text(task.get("status")).lower() != "done"
    ]

    return _limited_tasks(candidates)


def _suggested_first_action(command_center):
    overdue = sorted(command_center.get("overdue", []), key=_priority_rank)
    if overdue:
        return _slim_task(overdue[0])

    today = command_center.get("today", [])
    if today:
        return _slim_task(today[0])

    high_no_date = [
        task
        for task in command_center.get("no_date", [])
        if _display_text(task.get("priority")).lower() == "high"
    ]
    if high_no_date:
        return _slim_task(high_no_date[0])

    return None


def _compact_project_rollups(project_rollups):
    if not project_rollups:
        return {}

    return {
        "total_projects": project_rollups.get("total_projects", 0),
        "active_projects": project_rollups.get("active_projects", 0),
        "unlinked_tasks": project_rollups.get("unlinked_tasks", 0),
        "unlinked_memories": project_rollups.get("unlinked_memories", 0),
        "items": (project_rollups.get("items") or [])[:COMPACT_LIMIT],
        "unmatched_projects": (project_rollups.get("unmatched_projects") or [])[:COMPACT_LIMIT],
        "active_projects_without_links": (
            project_rollups.get("active_projects_without_links") or []
        )[:COMPACT_LIMIT],
    }


def _warnings(project_rollups):
    warnings = []

    if project_rollups.get("unlinked_tasks", 0):
        warnings.append("Some tasks are not linked to a project.")

    if project_rollups.get("unlinked_memories", 0):
        warnings.append("Some memories are not linked to a project.")

    if project_rollups.get("unmatched_project_tasks", 0) or project_rollups.get(
        "unmatched_project_memories", 0
    ):
        warnings.append("Some linked project names do not match a project record.")

    return warnings


def build_morning_brief(
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
    counts = _counts(command_center, memories, projects)

    return {
        "date": datetime.utcnow().date().isoformat(),
        "focus": _focus(counts),
        "counts": counts,
        "top_priorities": _top_priorities(command_center),
        "overdue_tasks": _limited_tasks(command_center.get("overdue", [])),
        "today_tasks": _limited_tasks(command_center.get("today", [])),
        "project_rollups": _compact_project_rollups(project_rollups),
        "suggested_first_action": _suggested_first_action(command_center),
        "warnings": _warnings(project_rollups),
    }
