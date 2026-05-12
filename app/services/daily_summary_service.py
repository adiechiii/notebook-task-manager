from datetime import datetime

from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.services.command_center_service import build_command_center


def _priority_bucket(tasks, priority):
    wanted = str(priority or "").strip().lower()

    return [
        task
        for task in tasks
        if str(task.get("status", "")).strip().lower() != "done"
        and str(task.get("priority", "")).strip().lower() == wanted
    ]


def _build_focus(task_totals, memory_total, project_total):
    parts = []

    if task_totals.get("today", 0):
        parts.append(f"You have {task_totals['today']} task(s) for today.")

    if task_totals.get("overdue", 0):
        parts.append(f"You have {task_totals['overdue']} overdue task(s).")

    if task_totals.get("no_date", 0):
        parts.append(f"You have {task_totals['no_date']} task(s) without dates.")

    if not parts:
        parts.append("No urgent dated tasks are waiting right now.")

    parts.append(f"You have {memory_total} saved memory item(s) and {project_total} active project(s).")

    return " ".join(parts)


def build_daily_summary(
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

    task_totals = {
        "today": len(command_center.get("today", [])),
        "overdue": len(command_center.get("overdue", [])),
        "upcoming": len(command_center.get("upcoming", [])),
        "no_date": len(command_center.get("no_date", [])),
        "done": len(command_center.get("done", [])),
    }

    memory_total = len(memories)
    active_projects = [
        project
        for project in projects
        if str(project.get("status", "")).strip().lower() == "active"
    ]
    project_total = len(active_projects)

    return {
        "date": datetime.utcnow().date().isoformat(),
        "summary": {
            "focus": _build_focus(task_totals, memory_total, project_total),
            "task_totals": task_totals,
            "memory_total": memory_total,
            "project_total": project_total,
        },
        "priorities": {
            "high": _priority_bucket(tasks, "High"),
            "medium": _priority_bucket(tasks, "Medium"),
            "low": _priority_bucket(tasks, "Low"),
        },
        "tasks": command_center,
        "memories": memories,
        "projects": active_projects,
    }
