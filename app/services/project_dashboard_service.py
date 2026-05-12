from datetime import datetime
import re

from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center


RECENT_MEMORY_LIMIT = 5
NEXT_ACTION_LIMIT = 5
COMPACT_BUCKET_LIMIT = 5


def _display_text(value):
    return str(value or "").strip()


def _link_key(value):
    return _display_text(value).lower()


def _normalized_key_part(value):
    return re.sub(r"\s+", " ", _display_text(value).lower())


def _parse_date(value):
    text = _display_text(value)
    if not text:
        return None

    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _memory_summary(memory):
    return (
        memory.get("memory_summary")
        or memory.get("summary")
        or memory.get("raw_text")
        or memory.get("text")
        or ""
    )


def _empty_task_counts():
    return {
        "total": 0,
        "by_status": {},
        "overdue": 0,
        "today": 0,
        "no_date": 0,
        "done": 0,
        "archived": 0,
    }


def _empty_response(query, match_type="none", include_details=False):
    response_mode = "full" if include_details else "compact"
    response = {
        "query": query,
        "matched": False,
        "match_type": match_type,
        "matched_project": None,
        "task_counts": _empty_task_counts(),
        "overdue_tasks": [],
        "today_tasks": [],
        "no_date_tasks": [],
        "recent_memories": [],
        "next_actions": [],
        "metadata": {
            "project_name": "",
            "response_mode": response_mode,
            "include_details": include_details,
            "uses_string_project_linking": True,
            "schema_changes": False,
            "linked_task_count": 0,
            "linked_memory_count": 0,
            "recent_memory_count_raw": 0,
            "recent_memory_count_deduped": 0,
        },
    }

    if include_details:
        response["linked_tasks"] = []
        response["linked_memories"] = []

    return response


def _match_project(query, projects):
    normalized_query = _link_key(query)
    if not normalized_query:
        return None, "none"

    for project in projects:
        if _link_key(project.get("name")) == normalized_query:
            return project, "exact"

    for project in projects:
        name = _link_key(project.get("name"))
        if normalized_query in name or name in normalized_query:
            return project, "substring"

    return None, "none"


def _task_from_sheet_row(row):
    return {
        "task_id": row.get("Task ID"),
        "text": row.get("Raw Text"),
        "title": row.get("Normalized Title"),
        "status": row.get("Status"),
        "page_date": _display_text(row.get("Page Date")),
        "category": row.get("Category"),
        "priority": row.get("Priority"),
        "project": row.get("Project"),
        "created_at": row.get("Created At"),
        "updated_at": row.get("Updated At"),
        "completion_date": row.get("Completion Date"),
    }


def _memory_from_sheet_row(row):
    return {
        "memory_id": row.get("Memory ID"),
        "text": row.get("Raw Text"),
        "summary": row.get("Memory Summary"),
        "type": row.get("Memory Type"),
        "entity": row.get("Entity"),
        "project": row.get("Project"),
        "tags": row.get("Tags"),
        "importance": row.get("Importance"),
        "status": row.get("Status"),
        "created_at": row.get("Created At"),
        "updated_at": row.get("Updated At"),
    }


def _get_all_task_rows(task_repo):
    return [_task_from_sheet_row(row) for row in task_repo.sheet.get_all_records()]


def _get_all_memory_rows(memory_repo):
    return [_memory_from_sheet_row(row) for row in memory_repo.sheet.get_all_records()]


def _status_counts(tasks):
    counts = _empty_task_counts()
    counts["total"] = len(tasks)

    for task in tasks:
        status = _display_text(task.get("status")) or "Unknown"
        counts["by_status"][status] = counts["by_status"].get(status, 0) + 1

        status_key = status.lower()
        if status_key == "done":
            counts["done"] += 1
        elif status_key == "archived":
            counts["archived"] += 1

    return counts


def _bucketed_linked_tasks(linked_tasks):
    active_tasks = [
        task
        for task in linked_tasks
        if _display_text(task.get("status")).lower() != "archived"
    ]
    return build_command_center(active_tasks)


def _recent_memories(linked_memories):
    return sorted(
        linked_memories,
        key=lambda memory: (
            _parse_date(memory.get("updated_at"))
            or _parse_date(memory.get("created_at"))
            or datetime.min
        ),
        reverse=True,
    )[:RECENT_MEMORY_LIMIT]


def _dedupe_recent_memories(memories):
    deduped = []
    seen = set()

    for memory in memories:
        key = (
            _normalized_key_part(_memory_summary(memory)),
            _normalized_key_part(memory.get("project")),
        )

        if not key[0] or key in seen:
            continue

        seen.add(key)
        deduped.append(memory)

    return deduped


def _next_actions(command_center):
    actions = []

    for bucket in ("overdue", "today", "no_date", "upcoming"):
        for task in command_center.get(bucket, []):
            status = _display_text(task.get("status")).lower()
            if status in {"done", "archived"}:
                continue

            actions.append(task)
            if len(actions) == NEXT_ACTION_LIMIT:
                return actions

    return actions


def _slim_task(task):
    return {
        "task_id": task.get("task_id"),
        "title": task.get("title") or task.get("text"),
        "status": task.get("status"),
        "page_date": task.get("page_date"),
        "category": task.get("category"),
        "priority": task.get("priority"),
        "project": task.get("project"),
    }


def _slim_memory(memory):
    return {
        "memory_id": memory.get("memory_id"),
        "summary": _memory_summary(memory),
        "type": memory.get("type"),
        "project": memory.get("project"),
        "tags": memory.get("tags"),
        "importance": memory.get("importance"),
        "created_at": memory.get("created_at"),
    }


def _limited_slim_tasks(tasks, limit=COMPACT_BUCKET_LIMIT):
    return [_slim_task(task) for task in tasks[:limit]]


def _project_metadata(
    project,
    linked_tasks,
    linked_memories,
    include_details,
    recent_memory_count_raw=None,
    recent_memory_count_deduped=None,
):
    response_mode = "full" if include_details else "compact"
    recent_memory_count_raw = (
        len(linked_memories)
        if recent_memory_count_raw is None
        else recent_memory_count_raw
    )
    recent_memory_count_deduped = (
        recent_memory_count_raw
        if recent_memory_count_deduped is None
        else recent_memory_count_deduped
    )

    return {
        "project_name": _display_text(project.get("name")),
        "response_mode": response_mode,
        "include_details": include_details,
        "uses_string_project_linking": True,
        "schema_changes": False,
        "linked_task_count": len(linked_tasks),
        "linked_memory_count": len(linked_memories),
        "recent_memory_count_raw": recent_memory_count_raw,
        "recent_memory_count_deduped": recent_memory_count_deduped,
    }


def _full_response(
    raw_query,
    match_type,
    matched_project,
    linked_tasks,
    linked_memories,
    task_counts,
    command_center,
):
    raw_recent_memories = _recent_memories(linked_memories)
    deduped_recent_memories = _dedupe_recent_memories(raw_recent_memories)

    return {
        "query": raw_query,
        "matched": True,
        "match_type": match_type,
        "matched_project": matched_project,
        "linked_tasks": linked_tasks,
        "linked_memories": linked_memories,
        "task_counts": task_counts,
        "overdue_tasks": command_center.get("overdue", []),
        "today_tasks": command_center.get("today", []),
        "no_date_tasks": command_center.get("no_date", []),
        "recent_memories": raw_recent_memories,
        "next_actions": _next_actions(command_center),
        "metadata": _project_metadata(
            matched_project,
            linked_tasks,
            linked_memories,
            include_details=True,
            recent_memory_count_raw=len(raw_recent_memories),
            recent_memory_count_deduped=len(deduped_recent_memories),
        ),
    }


def _compact_response(
    raw_query,
    match_type,
    matched_project,
    linked_tasks,
    linked_memories,
    task_counts,
    command_center,
):
    raw_recent_memories = _recent_memories(linked_memories)
    deduped_recent_memories = _dedupe_recent_memories(raw_recent_memories)
    recent_memories = [_slim_memory(memory) for memory in deduped_recent_memories]
    next_actions = [_slim_task(task) for task in _next_actions(command_center)]

    return {
        "query": raw_query,
        "matched": True,
        "match_type": match_type,
        "matched_project": matched_project,
        "task_counts": task_counts,
        "overdue_tasks": _limited_slim_tasks(command_center.get("overdue", [])),
        "today_tasks": _limited_slim_tasks(command_center.get("today", [])),
        "no_date_tasks": _limited_slim_tasks(command_center.get("no_date", [])),
        "recent_memories": recent_memories,
        "next_actions": next_actions,
        "metadata": _project_metadata(
            matched_project,
            linked_tasks,
            linked_memories,
            include_details=False,
            recent_memory_count_raw=len(raw_recent_memories),
            recent_memory_count_deduped=len(deduped_recent_memories),
        ),
    }


def build_project_dashboard(
    query,
    include_details=False,
    project_repo=None,
    task_repo=None,
    memory_repo=None,
):
    project_repo = project_repo or SheetsProjectRepository()
    task_repo = task_repo or SheetsTaskRepository()
    memory_repo = memory_repo or SheetsMemoryRepository()

    raw_query = str(query or "")
    projects = project_repo.search_projects("")
    matched_project, match_type = _match_project(raw_query, projects)

    if not matched_project:
        return _empty_response(raw_query, include_details=include_details)

    project_name = _display_text(matched_project.get("name"))
    project_key = _link_key(project_name)
    linked_tasks = [
        task
        for task in _get_all_task_rows(task_repo)
        if _link_key(task.get("project")) == project_key
    ]
    linked_memories = [
        memory
        for memory in _get_all_memory_rows(memory_repo)
        if _link_key(memory.get("project")) == project_key
    ]

    command_center = _bucketed_linked_tasks(linked_tasks)
    task_counts = _status_counts(linked_tasks)
    task_counts["overdue"] = len(command_center.get("overdue", []))
    task_counts["today"] = len(command_center.get("today", []))
    task_counts["no_date"] = len(command_center.get("no_date", []))

    if include_details:
        return _full_response(
            raw_query,
            match_type,
            matched_project,
            linked_tasks,
            linked_memories,
            task_counts,
            command_center,
        )

    return _compact_response(
        raw_query,
        match_type,
        matched_project,
        linked_tasks,
        linked_memories,
        task_counts,
        command_center,
    )
