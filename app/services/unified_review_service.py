from datetime import datetime
from typing import Any

from app.repositories.sheets_decision_repository import SheetsDecisionRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center
from app.services.night_review_service import build_night_review
from app.services.project_rollup_service import build_project_rollups
from app.services.weekly_review_service import build_weekly_review


VALID_PERIODS = {"nightly", "weekly", "monthly", "quarterly", "annual"}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    return " ".join(_clean(value).lower().split())


def _safe_limit(value: int | None) -> int:
    try:
        limit = int(value or 10)
    except (TypeError, ValueError):
        limit = 10

    return min(max(limit, 1), 25)


def _safe_period(value: str) -> str:
    period = _key(value)
    if period in VALID_PERIODS:
        return period
    return "weekly"


def _project_matches(value: Any, project: str) -> bool:
    wanted = _key(project)
    if not wanted:
        return True

    current = _key(value)
    return bool(current and (current == wanted or wanted in current or current in wanted))


def _filter_tasks(tasks: list[dict[str, Any]], project: str) -> list[dict[str, Any]]:
    if not _clean(project):
        return tasks
    return [task for task in tasks if _project_matches(task.get("project"), project)]


def _filter_memories(memories: list[dict[str, Any]], project: str) -> list[dict[str, Any]]:
    if not _clean(project):
        return memories
    return [memory for memory in memories if _project_matches(memory.get("project"), project)]


def _filter_projects(projects: list[dict[str, Any]], project: str) -> list[dict[str, Any]]:
    if not _clean(project):
        return projects
    return [item for item in projects if _project_matches(item.get("name"), project)]


def _slim_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": task.get("title") or task.get("text"),
        "text": task.get("text"),
        "status": task.get("status"),
        "page_date": task.get("page_date"),
        "category": task.get("category"),
        "priority": task.get("priority"),
        "project": task.get("project"),
    }


def _slim_memory(memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "text": memory.get("text") or memory.get("summary"),
        "summary": memory.get("summary") or memory.get("text"),
        "type": memory.get("type"),
        "project": memory.get("project"),
        "tags": memory.get("tags"),
        "importance": memory.get("importance"),
        "status": memory.get("status"),
    }


def _slim_decision(decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "decision": decision.get("decision"),
        "project": decision.get("project"),
        "status": decision.get("status"),
        "importance": decision.get("importance"),
        "rationale": decision.get("rationale"),
        "outcome": decision.get("outcome"),
        "created_at": decision.get("created_at"),
        "updated_at": decision.get("updated_at"),
    }


def _limited(items: list[Any], limit: int) -> list[Any]:
    return list(items or [])[:limit]


def _priority_key(task: dict[str, Any]) -> int:
    priority = _key(task.get("priority"))
    if priority == "high":
        return 0
    if priority == "medium":
        return 1
    if priority == "low":
        return 2
    return 3


def _active_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        project
        for project in projects
        if _key(project.get("status")) == "active"
    ]


def _decision_search(decision_repo, project: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        result = decision_repo.search_decisions(project=project or "", limit=100)
    except Exception:
        warnings.append("Decision search failed; unified review returned without decision context.")
        return []

    warnings.extend(result.get("warnings", []))
    return result.get("decisions", [])


def _important_decisions(decisions: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    items = [
        decision
        for decision in decisions
        if _key(decision.get("importance")) == "high"
    ]
    return [_slim_decision(decision) for decision in _limited(items, limit)]


def _recent_decisions(decisions: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    sorted_decisions = sorted(
        decisions,
        key=lambda decision: _clean(decision.get("created_at") or decision.get("updated_at")),
        reverse=True,
    )
    return [_slim_decision(decision) for decision in _limited(sorted_decisions, limit)]


def _decisions_needing_followup(decisions: list[dict[str, Any]], tasks: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    task_projects = {_key(task.get("project")) for task in tasks if _key(task.get("project"))}
    followup = []

    for decision in decisions:
        project_key = _key(decision.get("project"))
        importance = _key(decision.get("importance"))

        if importance != "high":
            continue

        if not project_key or project_key not in task_projects:
            item = _slim_decision(decision)
            item["reason"] = "High-importance decision has no clearly linked active task project."
            followup.append(item)

    return followup[:limit]


def _important_memories(memories: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    items = [
        memory
        for memory in memories
        if _key(memory.get("importance")) in {"high", "medium"}
        or _key(memory.get("type")) in {"instruction", "preference", "project", "business"}
    ]
    return [_slim_memory(memory) for memory in _limited(items, limit)]


def _recent_memories(memories: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return [_slim_memory(memory) for memory in _limited(memories, limit)]


def _project_memories(memories: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    items = [memory for memory in memories if _key(memory.get("project"))]
    return [_slim_memory(memory) for memory in _limited(items, limit)]


def _unfinished_work(command_center: dict[str, list[dict[str, Any]]], limit: int) -> dict[str, Any]:
    return {
        "overdue_tasks": [_slim_task(task) for task in _limited(command_center.get("overdue", []), limit)],
        "today_tasks": [_slim_task(task) for task in _limited(command_center.get("today", []), limit)],
        "no_date_tasks": [_slim_task(task) for task in _limited(command_center.get("no_date", []), limit)],
        "upcoming_tasks": [_slim_task(task) for task in _limited(command_center.get("upcoming", []), limit)],
    }


def _project_momentum(project_rollups: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    momentum = []

    for item in (project_rollups.get("items") or [])[:limit]:
        state = "Active"

        if item.get("overdue", 0):
            state = "Needs Attention"
        elif item.get("done", 0):
            state = "Completed Recently"
        elif not item.get("task_count", 0) and not item.get("memory_count", 0):
            state = "No Recent Signal"

        momentum.append(
            {
                "project": item.get("project"),
                "momentum": state,
                "task_count": item.get("task_count", 0),
                "memory_count": item.get("memory_count", 0),
                "overdue": item.get("overdue", 0),
                "done": item.get("done", 0),
            }
        )

    return momentum


def _progress(command_center, projects, project_rollups, limit: int) -> dict[str, Any]:
    completed_tasks = [_slim_task(task) for task in _limited(command_center.get("done", []), limit)]

    return {
        "completed_tasks": completed_tasks,
        "completed_count": len(command_center.get("done", [])),
        "active_projects": _limited(_active_projects(projects), limit),
        "project_momentum": _project_momentum(project_rollups, limit),
    }


def _blockers(command_center, project_rollups, decisions, limit: int) -> list[dict[str, Any]]:
    blockers = []

    overdue_count = len(command_center.get("overdue", []))
    if overdue_count:
        blockers.append(
            {
                "type": "overdue_work",
                "severity": "High" if overdue_count >= 5 else "Medium",
                "description": f"{overdue_count} overdue task(s) remain unfinished.",
                "suggested_action": "Clear, reschedule, or intentionally defer overdue tasks.",
            }
        )

    no_date_count = len(command_center.get("no_date", []))
    if no_date_count >= 5:
        blockers.append(
            {
                "type": "no_date_backlog",
                "severity": "Medium",
                "description": f"{no_date_count} active task(s) do not have dates.",
                "suggested_action": "Add dates to the most important no-date tasks.",
            }
        )

    unlinked_tasks = project_rollups.get("unlinked_tasks", 0)
    if unlinked_tasks:
        blockers.append(
            {
                "type": "unlinked_tasks",
                "severity": "Medium",
                "description": f"{unlinked_tasks} task(s) are not linked to a project.",
                "suggested_action": "Assign important tasks to active projects.",
            }
        )

    high_decisions_without_project = [
        decision
        for decision in decisions
        if _key(decision.get("importance")) == "high" and not _key(decision.get("project"))
    ]
    if high_decisions_without_project:
        blockers.append(
            {
                "type": "unlinked_high_importance_decisions",
                "severity": "Medium",
                "description": f"{len(high_decisions_without_project)} high-importance decision(s) are not linked to a project.",
                "suggested_action": "Link strategic decisions to projects.",
            }
        )

    return blockers[:limit]


def _patterns(command_center, project_rollups, memories, period: str, limit: int) -> list[dict[str, Any]]:
    patterns = []

    if len(command_center.get("overdue", [])) >= 3:
        patterns.append(
            {
                "type": "overdue_pressure",
                "description": "Several overdue tasks remain unresolved.",
                "evidence": [f"{len(command_center.get('overdue', []))} overdue tasks"],
                "suggested_action": "Reduce overdue work before adding more commitments.",
            }
        )

    categories: dict[str, int] = {}
    for task in command_center.get("overdue", []):
        category = _clean(task.get("category")) or "Uncategorized"
        categories[category] = categories.get(category, 0) + 1

    repeated_categories = [
        {"category": category, "overdue_count": count}
        for category, count in categories.items()
        if count >= 2
    ]
    if repeated_categories:
        patterns.append(
            {
                "type": "repeated_overdue_categories",
                "description": "Some categories repeatedly appear in overdue work.",
                "evidence": repeated_categories,
                "suggested_action": "Batch or reschedule these categories deliberately.",
            }
        )

    if project_rollups.get("unlinked_memories", 0):
        patterns.append(
            {
                "type": "unlinked_memory_context",
                "description": "Some memories are not connected to projects.",
                "evidence": [f"{project_rollups.get('unlinked_memories')} unlinked memories"],
                "suggested_action": "Link important memories to projects for better context.",
            }
        )

    if period in {"monthly", "quarterly", "annual"}:
        patterns.append(
            {
                "type": "limited_historical_depth",
                "description": f"{period.title()} review is currently based on available task, project, memory, and decision state.",
                "evidence": ["Historical trend storage is not fully implemented yet."],
                "suggested_action": "Treat this as a current-state strategic review.",
            }
        )

    return patterns[:limit]


def _risks(command_center, project_rollups, limit: int) -> list[dict[str, Any]]:
    risks = []

    high_overdue = [
        task
        for task in command_center.get("overdue", [])
        if _key(task.get("priority")) == "high"
    ]
    if high_overdue:
        risks.append(
            {
                "type": "high_priority_overdue",
                "severity": "Critical",
                "reason": f"{len(high_overdue)} high-priority task(s) are overdue.",
                "suggested_action": "Resolve or reschedule high-priority overdue tasks.",
            }
        )

    if len(command_center.get("overdue", [])) >= 5:
        risks.append(
            {
                "type": "overload",
                "severity": "High",
                "reason": "Overdue task count is high.",
                "suggested_action": "Reduce active work-in-progress.",
            }
        )

    if project_rollups.get("active_projects_without_links"):
        risks.append(
            {
                "type": "stale_active_projects",
                "severity": "Medium",
                "reason": "Some active projects have no linked tasks or memories.",
                "suggested_action": "Add one next action or archive inactive projects.",
            }
        )

    return risks[:limit]


def _review_status(command_center, risks, period: str) -> str:
    if any(_key(risk.get("severity")) == "critical" for risk in risks):
        return "At Risk"

    if len(command_center.get("overdue", [])) >= 5:
        return "Overloaded"

    if period in {"monthly", "quarterly", "annual"} and risks:
        return "Strategic Review Needed"

    if command_center.get("overdue") or len(command_center.get("no_date", [])) >= 5:
        return "Needs Attention"

    return "Clear"


def _recommended_focus(command_center, project_rollups, decisions, limit: int) -> list[dict[str, Any]]:
    focus = []

    candidate_tasks = []
    for bucket in ("overdue", "today", "no_date", "upcoming"):
        candidate_tasks.extend(command_center.get(bucket, []))

    candidate_tasks = sorted(candidate_tasks, key=_priority_key)
    for task in candidate_tasks[:3]:
        focus.append(
            {
                "title": task.get("title") or task.get("text"),
                "project": task.get("project"),
                "reason": "Selected from unfinished priority work.",
                "next_action": task.get("title") or task.get("text"),
            }
        )

    high_decisions = [
        decision
        for decision in decisions
        if _key(decision.get("importance")) == "high"
    ]
    if high_decisions:
        decision = high_decisions[0]
        focus.append(
            {
                "title": "Align execution with high-importance decision",
                "project": decision.get("project"),
                "reason": decision.get("decision"),
                "next_action": "Make sure current tasks support this decision.",
            }
        )

    return focus[:limit]


def _carryover(command_center, decisions, limit: int) -> list[dict[str, Any]]:
    carryover = []

    for bucket in ("overdue", "today", "no_date"):
        for task in command_center.get(bucket, []):
            if _key(task.get("status")) in {"done", "archived"}:
                continue

            reason = "Unfinished work should carry forward."
            if bucket == "overdue":
                reason = "Overdue and still unfinished."
            elif bucket == "today":
                reason = "Due today and not completed."
            elif _key(task.get("priority")) == "high":
                reason = "High-priority no-date task."

            carryover.append(
                {
                    "title": task.get("title") or task.get("text"),
                    "project": task.get("project"),
                    "reason": reason,
                }
            )

            if len(carryover) >= limit:
                return carryover

    return carryover[:limit]


def _period_review(
    period: str,
    task_repo,
    memory_repo,
    project_repo,
    warnings: list[str],
) -> dict[str, Any]:
    if period == "nightly":
        try:
            return build_night_review(
                task_repo=task_repo,
                memory_repo=memory_repo,
                project_repo=project_repo,
            )
        except Exception:
            warnings.append("Nightly review detail failed; unified review returned general review data.")
            return {}

    if period == "weekly":
        try:
            return build_weekly_review(
                task_repo=task_repo,
                memory_repo=memory_repo,
                project_repo=project_repo,
            )
        except Exception:
            warnings.append("Weekly review detail failed; unified review returned general review data.")
            return {}

    return {
        "mode": "current_state_strategic_review",
        "message": f"{period.title()} review uses current available task, project, memory, and decision data until deeper historical trend storage exists.",
    }


def _warnings(project_rollups, decision_warnings, period: str, project: str, scoped_tasks, scoped_projects) -> list[str]:
    warnings = list(decision_warnings or [])

    if project and not scoped_tasks and not scoped_projects:
        warnings.append("Project filter returned no matching tasks or projects.")

    if project_rollups.get("unlinked_tasks", 0):
        warnings.append("Some tasks are not linked to a project.")

    if project_rollups.get("unlinked_memories", 0):
        warnings.append("Some memories are not linked to a project.")

    if project_rollups.get("unmatched_project_tasks", 0) or project_rollups.get("unmatched_project_memories", 0):
        warnings.append("Some linked project names do not match a project record.")

    if period in {"monthly", "quarterly", "annual"}:
        warnings.append(f"{period.title()} review is conservative because long-term historical analytics are not fully implemented yet.")

    return warnings


def _headline(period: str, command_center: dict[str, list[dict[str, Any]]], projects: list[dict[str, Any]]) -> str:
    return (
        f"{period.title()} review shows "
        f"{len(command_center.get('done', []))} completed visible task(s), "
        f"{len(command_center.get('overdue', []))} overdue task(s), "
        f"{len(command_center.get('no_date', []))} no-date task(s), and "
        f"{len(_active_projects(projects))} active project(s)."
    )


def build_unified_review(
    *,
    period: str = "weekly",
    project: str = "",
    limit: int = 10,
    task_repo=None,
    memory_repo=None,
    project_repo=None,
    decision_repo=None,
) -> dict[str, Any]:
    safe_period = _safe_period(period)
    requested_project = _clean(project)
    safe_limit = _safe_limit(limit)

    task_repo = task_repo or SheetsTaskRepository()
    memory_repo = memory_repo or SheetsMemoryRepository()
    project_repo = project_repo or SheetsProjectRepository()
    decision_repo = decision_repo or SheetsDecisionRepository()

    all_tasks = task_repo.get_command_center_tasks()
    all_memories = memory_repo.search_memories("")
    all_projects = project_repo.search_projects("")

    scoped_tasks = _filter_tasks(all_tasks, requested_project)
    scoped_memories = _filter_memories(all_memories, requested_project)
    scoped_projects = _filter_projects(all_projects, requested_project)

    command_center = build_command_center(scoped_tasks)
    project_rollups = build_project_rollups(
        scoped_tasks,
        scoped_memories,
        scoped_projects,
        command_center,
    )

    decision_warnings: list[str] = []
    decisions = _decision_search(decision_repo, requested_project, decision_warnings)

    blockers = _blockers(command_center, project_rollups, decisions, safe_limit)
    patterns = _patterns(command_center, project_rollups, scoped_memories, safe_period, safe_limit)
    risks = _risks(command_center, project_rollups, safe_limit)
    review_status = _review_status(command_center, risks, safe_period)
    warnings = _warnings(
        project_rollups,
        decision_warnings,
        safe_period,
        requested_project,
        scoped_tasks,
        scoped_projects,
    )

    period_review = _period_review(
        safe_period,
        task_repo,
        memory_repo,
        project_repo,
        warnings,
    )

    return {
        "dry_run": True,
        "writes": False,
        "generated_at": datetime.utcnow().isoformat(),
        "scope": {
            "period": safe_period,
            "project": requested_project,
            "limit": safe_limit,
        },
        "summary": {
            "headline": _headline(safe_period, command_center, scoped_projects),
            "review_status": review_status,
            "main_takeaway": (
                "Resolve overdue/high-priority work before expanding scope."
                if risks or blockers
                else "Current review is clear with no major blockers detected."
            ),
        },
        "progress": _progress(command_center, scoped_projects, project_rollups, safe_limit),
        "unfinished_work": _unfinished_work(command_center, safe_limit),
        "decisions": {
            "important_decisions": _important_decisions(decisions, safe_limit),
            "recent_decisions": _recent_decisions(decisions, safe_limit),
            "decisions_needing_followup": _decisions_needing_followup(decisions, scoped_tasks, safe_limit),
        },
        "memories": {
            "important_memories": _important_memories(scoped_memories, safe_limit),
            "recent_memories": _recent_memories(scoped_memories, safe_limit),
            "project_memories": _project_memories(scoped_memories, safe_limit),
        },
        "blockers": blockers,
        "patterns": patterns,
        "risks": risks,
        "recommended_focus": _recommended_focus(command_center, project_rollups, decisions, safe_limit),
        "carryover": _carryover(command_center, decisions, safe_limit),
        "period_review": period_review,
        "warnings": warnings,
    }
