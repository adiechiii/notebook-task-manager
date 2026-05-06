from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.services.command_center_service import build_command_center


def _clean_bucket(value, default):
    text = str(value or "").strip()
    return text if text else default


def _count_by(items, key, default):
    counts = {}

    for item in items:
        bucket = _clean_bucket(item.get(key), default)
        counts[bucket] = counts.get(bucket, 0) + 1

    return dict(sorted(counts.items()))


def _count_active(items):
    return sum(
        1
        for item in items
        if str(item.get("status", "")).strip().lower() == "active"
    )


def build_weekly_review(
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

    return {
        "tasks": {
            "total": len(tasks),
            "today": len(command_center.get("today", [])),
            "overdue": len(command_center.get("overdue", [])),
            "upcoming": len(command_center.get("upcoming", [])),
            "no_date": len(command_center.get("no_date", [])),
            "done": len(command_center.get("done", [])),
        },
        "categories": _count_by(tasks, "category", "Uncategorized"),
        "priorities": _count_by(tasks, "priority", "Unprioritized"),
        "memories": {
            "total": len(memories),
            "active": _count_active(memories),
        },
        "projects": {
            "total": len(projects),
            "active": _count_active(projects),
        },
    }
