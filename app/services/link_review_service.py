from typing import Any

from app.repositories.sheets_decision_repository import SheetsDecisionRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository


VALID_AREAS = {"all", "tasks", "memories", "decisions"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    return " ".join(_clean(value).casefold().split())


def _safe_limit(value: int) -> int:
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = 50

    return min(max(limit, 1), 200)


def _base_area_summary() -> dict[str, int]:
    return {
        "checked": 0,
        "missing_project_links": 0,
        "invalid_project_links": 0,
        "valid_project_links": 0,
    }


def _area_label(area: str) -> str:
    labels = {
        "tasks": "Task",
        "memories": "Memory",
        "decisions": "Decision",
    }
    return labels.get(area, area.title())


def _item(area: str, item_id: Any, title: Any, project: Any, issue_type: str, message: str) -> dict[str, Any]:
    return {
        "area": area,
        "item_id": _clean(item_id) or None,
        "title": _clean(title) or None,
        "project": _clean(project) or None,
        "issue_type": issue_type,
        "message": message,
    }


def _review_items(
    *,
    area: str,
    rows: list[dict[str, Any]],
    valid_project_keys: set[str],
    include_valid_links: bool,
    limit: int,
) -> tuple[dict[str, int], list[dict[str, Any]], list[dict[str, Any]]]:
    summary = _base_area_summary()
    issues = []
    valid_links = []

    for row in rows:
        project = _clean(row.get("project"))
        project_key = _key(project)

        summary["checked"] += 1

        if not project:
            summary["missing_project_links"] += 1
            if len(issues) < limit:
                issues.append(
                    _item(
                        area=area,
                        item_id=row.get("id"),
                        title=row.get("title"),
                        project=project,
                        issue_type="missing_project_link",
                        message=f"{_area_label(area)} is missing a project link.",
                    )
                )
            continue

        if project_key not in valid_project_keys:
            summary["invalid_project_links"] += 1
            if len(issues) < limit:
                issues.append(
                    _item(
                        area=area,
                        item_id=row.get("id"),
                        title=row.get("title"),
                        project=project,
                        issue_type="invalid_project_link",
                        message=f"Project '{project}' does not match an existing project.",
                    )
                )
            continue

        summary["valid_project_links"] += 1
        if include_valid_links and len(valid_links) < limit:
            valid_links.append(
                _item(
                    area=area,
                    item_id=row.get("id"),
                    title=row.get("title"),
                    project=project,
                    issue_type="valid_project_link",
                    message=f"Project '{project}' matches an existing project.",
                )
            )

    return summary, issues, valid_links


def _task_rows() -> list[dict[str, Any]]:
    repo = SheetsTaskRepository()
    return [
        {
            "id": task.get("Task ID"),
            "title": task.get("Normalized Title") or task.get("Raw Text"),
            "project": task.get("Project"),
        }
        for task in repo.read_tasks()
    ]


def _memory_rows() -> list[dict[str, Any]]:
    repo = SheetsMemoryRepository()
    return [
        {
            "id": memory.get("memory_id"),
            "title": memory.get("summary") or memory.get("text"),
            "project": memory.get("project"),
        }
        for memory in repo.search_memories("")
    ]


def _decision_rows(warnings: list[str]) -> list[dict[str, Any]]:
    repo = SheetsDecisionRepository()
    inspection = repo.inspect_schema()

    if not inspection.get("exists") or inspection.get("headers_match") is not True:
        warnings.extend(inspection.get("warnings", []))
        return []

    return [
        {
            "id": decision.get("Decision ID"),
            "title": decision.get("Decision"),
            "project": decision.get("Project"),
        }
        for decision in repo.read_decisions()
    ]


def build_link_review(
    *,
    include_valid_links: bool = False,
    limit: int = 50,
    area: str = "all",
) -> dict[str, Any]:
    requested_area = _key(area) or "all"
    if requested_area not in VALID_AREAS:
        requested_area = "all"

    safe_limit = _safe_limit(limit)
    warnings: list[str] = []
    recommendations: list[str] = []

    project_repo = SheetsProjectRepository()
    projects = project_repo.search_projects("")
    valid_project_keys = {
        _key(project.get("name"))
        for project in projects
        if _key(project.get("name"))
    }

    summary = {
        "projects_available": len(valid_project_keys),
        "tasks": _base_area_summary(),
        "memories": _base_area_summary(),
        "decisions": _base_area_summary(),
    }
    issues: list[dict[str, Any]] = []
    valid_links: list[dict[str, Any]] = []

    area_rows = {}
    if requested_area in {"all", "tasks"}:
        area_rows["tasks"] = _task_rows()
    if requested_area in {"all", "memories"}:
        area_rows["memories"] = _memory_rows()
    if requested_area in {"all", "decisions"}:
        area_rows["decisions"] = _decision_rows(warnings)

    for current_area, rows in area_rows.items():
        area_summary, area_issues, area_valid_links = _review_items(
            area=current_area,
            rows=rows,
            valid_project_keys=valid_project_keys,
            include_valid_links=include_valid_links,
            limit=safe_limit,
        )
        summary[current_area] = area_summary
        remaining_issue_slots = max(safe_limit - len(issues), 0)
        remaining_valid_slots = max(safe_limit - len(valid_links), 0)
        issues.extend(area_issues[:remaining_issue_slots])
        valid_links.extend(area_valid_links[:remaining_valid_slots])

    total_missing = sum(summary[name]["missing_project_links"] for name in ("tasks", "memories", "decisions"))
    total_invalid = sum(summary[name]["invalid_project_links"] for name in ("tasks", "memories", "decisions"))

    if not valid_project_keys:
        warnings.append("No existing projects were found. Link validation cannot confirm valid project names.")

    if total_missing:
        recommendations.append("Review missing project links and add a project where the context is clear.")
    if total_invalid:
        recommendations.append("Rename invalid project links to match an existing project exactly, or create the missing project first.")
    if not recommendations:
        recommendations.append("No project link issues were found for the requested area.")

    return {
        "ok": not warnings and total_missing == 0 and total_invalid == 0,
        "area": requested_area,
        "include_valid_links": include_valid_links,
        "limit": safe_limit,
        "summary": summary,
        "issues": issues,
        "valid_links": valid_links,
        "warnings": warnings,
        "recommendations": recommendations,
    }
