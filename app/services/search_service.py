from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository


def _normalize_query(query: str) -> str:
    return str(query or "").strip().lower()


def _matches_query(item: dict, keys: list[str], query: str) -> bool:
    if not query:
        return True

    searchable = " ".join(str(item.get(key, "")) for key in keys).lower()
    return query in searchable


def _task_result(task: dict) -> dict:
    title = task.get("title") or task.get("text") or ""

    return {
        "type": "task",
        "title": title,
        "text": task.get("text", ""),
        "data": task,
    }


def _memory_result(memory: dict) -> dict:
    title = memory.get("summary") or memory.get("text") or ""

    return {
        "type": "memory",
        "title": title,
        "text": memory.get("text", ""),
        "data": memory,
    }


def _project_result(project: dict) -> dict:
    title = project.get("name") or ""
    text = project.get("description") or project.get("goal") or ""

    return {
        "type": "project",
        "title": title,
        "text": text,
        "data": project,
    }


def build_search_everything(
    query: str = "",
    task_repo=None,
    memory_repo=None,
    project_repo=None,
):
    task_repo = task_repo or SheetsTaskRepository()
    memory_repo = memory_repo or SheetsMemoryRepository()
    project_repo = project_repo or SheetsProjectRepository()

    raw_query = str(query or "")
    normalized_query = _normalize_query(raw_query)

    all_tasks = task_repo.get_command_center_tasks()
    tasks = [
        task
        for task in all_tasks
        if _matches_query(
            task,
            ["text", "title", "status", "page_date", "category", "priority"],
            normalized_query,
        )
    ]

    memories = memory_repo.search_memories(raw_query)
    projects = project_repo.search_projects(raw_query)

    task_results = [_task_result(task) for task in tasks]
    memory_results = [_memory_result(memory) for memory in memories]
    project_results = [_project_result(project) for project in projects]

    results = task_results + memory_results + project_results

    return {
        "query": raw_query,
        "count": len(results),
        "tasks": {
            "count": len(task_results),
            "results": task_results,
        },
        "memories": {
            "count": len(memory_results),
            "results": memory_results,
        },
        "projects": {
            "count": len(project_results),
            "results": project_results,
        },
        "results": results,
    }
