from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_decision_repository import SheetsDecisionRepository
from app.repositories.sheets_thought_repository import SheetsThoughtRepository


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


def _decision_result(decision: dict) -> dict:
    title = decision.get("decision") or ""

    return {
        "type": "decision",
        "title": title,
        "text": title,
        "data": decision,
    }


def _thought_result(thought: dict) -> dict:
    title = thought.get("summary") or thought.get("raw_thought") or ""

    return {
        "type": "thought",
        "title": title,
        "text": thought.get("raw_thought", ""),
        "data": thought,
    }


def build_search_everything(
    query: str = "",
    task_repo=None,
    memory_repo=None,
    project_repo=None,
    decision_repo=None,
    thought_repo=None,
):
    task_repo = task_repo or SheetsTaskRepository()
    memory_repo = memory_repo or SheetsMemoryRepository()
    project_repo = project_repo or SheetsProjectRepository()
    decision_repo = decision_repo or SheetsDecisionRepository()
    thought_repo = thought_repo or SheetsThoughtRepository()

    raw_query = str(query or "")
    normalized_query = _normalize_query(raw_query)

    all_tasks = task_repo.get_command_center_tasks()
    tasks = [
        task
        for task in all_tasks
        if _matches_query(
            task,
            ["text", "title", "status", "page_date", "category", "priority", "project"],
            normalized_query,
        )
    ]

    memories = memory_repo.search_memories(raw_query)
    projects = project_repo.search_projects(raw_query)

    try:
        decision_search = decision_repo.search_decisions(raw_query, limit=50)
        decisions = decision_search.get("decisions", [])
        decision_warnings = decision_search.get("warnings", [])
    except Exception:
        decisions = []
        decision_warnings = ["Decision search failed; returning other search results."]

    try:
        thought_search = thought_repo.search_thoughts(raw_query, limit=50)
        thoughts = thought_search.get("thoughts", [])
        thought_warnings = thought_search.get("warnings", [])
    except Exception:
        thoughts = []
        thought_warnings = ["Thought search failed; returning other search results."]

    task_results = [_task_result(task) for task in tasks]
    memory_results = [_memory_result(memory) for memory in memories]
    project_results = [_project_result(project) for project in projects]
    decision_results = [_decision_result(decision) for decision in decisions]
    thought_results = [_thought_result(thought) for thought in thoughts]

    results = task_results + memory_results + project_results + decision_results + thought_results

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
        "decisions": {
            "count": len(decision_results),
            "results": decision_results,
            "warnings": decision_warnings,
        },
        "thoughts": {
            "count": len(thought_results),
            "results": thought_results,
            "warnings": thought_warnings,
        },
        "results": results,
    }
