from datetime import datetime
from typing import Any

from app.repositories.sheets_decision_repository import SheetsDecisionRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center
from app.services.project_rollup_service import build_project_rollups


VALID_MODES = {"overview", "today", "focus", "project"}
TASK_BUCKETS = ("today", "overdue", "upcoming", "no_date", "done")


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


def _safe_mode(value: str) -> str:
    mode = _key(value)
    if mode in VALID_MODES:
        return mode
    return "overview"


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


def _date_from_task(task: dict[str, Any]):
    value = _clean(task.get("page_date"))
    if not value:
        return None

    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _status(task: dict[str, Any]) -> str:
    return _key(task.get("status"))


def _priority(task: dict[str, Any]) -> str:
    return _key(task.get("priority"))


def _is_active_task(task: dict[str, Any]) -> bool:
    return _status(task) not in {"done", "archived"}


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
    }


def _limited(items: list[Any], limit: int) -> list[Any]:
    return list(items or [])[:limit]


def _task_score(task: dict[str, Any], bucket: str, high_decision_projects: set[str]) -> int:
    score = 0

    if bucket == "overdue":
        score += 50
    elif bucket == "today":
        score += 40
    elif bucket == "upcoming":
        score += 10
    elif bucket == "no_date":
        score -= 5

    priority = _priority(task)
    if priority == "high":
        score += 30
    elif priority == "medium":
        score += 20
    elif priority == "low":
        score += 5

    project = _key(task.get("project"))
    if project:
        score += 10
        if project in high_decision_projects:
            score += 25
    else:
        score -= 10

    text = _key(f"{task.get('title', '')} {task.get('text', '')}")
    urgency_words = ("urgent", "asap", "important", "today", "tomorrow", "deadline")
    if any(word in text for word in urgency_words):
        score += 15

    return score


def _rank_focus_tasks(
    command_center: dict[str, list[dict[str, Any]]],
    high_decision_projects: set[str],
    limit: int,
) -> list[dict[str, Any]]:
    candidates = []

    for bucket in ("overdue", "today", "no_date", "upcoming"):
        for task in command_center.get(bucket, []):
            if not _is_active_task(task):
                continue

            slim = _slim_task(task)
            slim["score"] = _task_score(task, bucket, high_decision_projects)
            slim["reason"] = _focus_reason(task, bucket, high_decision_projects)
            candidates.append(slim)

    candidates.sort(key=lambda item: item.get("score", 0), reverse=True)
    return candidates[:limit]


def _focus_reason(task: dict[str, Any], bucket: str, high_decision_projects: set[str]) -> str:
    reasons = []

    if bucket == "overdue":
        reasons.append("overdue")
    elif bucket == "today":
        reasons.append("due today")
    elif bucket == "no_date":
        reasons.append("no date")
    elif bucket == "upcoming":
        reasons.append("upcoming")

    priority = _clean(task.get("priority"))
    if priority:
        reasons.append(f"{priority} priority")

    project = _key(task.get("project"))
    if project and project in high_decision_projects:
        reasons.append("linked to high-importance decision")

    if not reasons:
        return "Selected from active task list."

    return "Selected because it is " + ", ".join(reasons) + "."


def _bucketed_slim_tasks(command_center: dict[str, list[dict[str, Any]]], limit: int) -> dict[str, Any]:
    return {
        "today": [_slim_task(task) for task in _limited(command_center.get("today", []), limit)],
        "overdue": [_slim_task(task) for task in _limited(command_center.get("overdue", []), limit)],
        "upcoming": [_slim_task(task) for task in _limited(command_center.get("upcoming", []), limit)],
        "no_date": [_slim_task(task) for task in _limited(command_center.get("no_date", []), limit)],
        "done_recently": [_slim_task(task) for task in _limited(command_center.get("done", []), limit)],
    }


def _decision_search(decision_repo, project: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        result = decision_repo.search_decisions(
            project=project or "",
            limit=100,
        )
    except Exception:
        warnings.append("Decision search failed; dashboard returned without decision context.")
        return []

    warnings.extend(result.get("warnings", []))
    return result.get("decisions", [])


def _high_importance_decisions(decisions: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    high = [
        decision
        for decision in decisions
        if _key(decision.get("importance")) == "high"
    ]
    return [_slim_decision(decision) for decision in high[:limit]]


def _high_decision_projects(decisions: list[dict[str, Any]]) -> set[str]:
    return {
        _key(decision.get("project"))
        for decision in decisions
        if _key(decision.get("importance")) == "high" and _key(decision.get("project"))
    }


def _project_next_action(project_name: str, command_center: dict[str, list[dict[str, Any]]]) -> dict[str, Any] | None:
    for bucket in ("overdue", "today", "no_date", "upcoming"):
        for task in command_center.get(bucket, []):
            if _project_matches(task.get("project"), project_name) and _is_active_task(task):
                return _slim_task(task)

    return None


def _project_momentum(item: dict[str, Any]) -> str:
    if item.get("overdue", 0):
        return "Needs Attention"
    if item.get("today", 0):
        return "Active"
    if item.get("done", 0):
        return "Completed Recently"
    if item.get("task_count", 0) or item.get("memory_count", 0):
        return "Active"
    return "No Recent Signal"


def _project_risk_level(item: dict[str, Any]) -> str:
    if item.get("overdue", 0) >= 3:
        return "High"
    if item.get("overdue", 0):
        return "Medium"
    if item.get("no_date", 0) >= 5:
        return "Medium"
    return "Low"


def _dashboard_project_rollups(
    raw_rollups: dict[str, Any],
    command_center: dict[str, list[dict[str, Any]]],
    decisions: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    decision_count_by_project: dict[str, int] = {}

    for decision in decisions:
        key = _key(decision.get("project"))
        if key:
            decision_count_by_project[key] = decision_count_by_project.get(key, 0) + 1

    items = []
    for item in raw_rollups.get("items", []):
        project_name = item.get("project")
        project_key = _key(project_name)

        enriched = {
            **item,
            "decision_count": decision_count_by_project.get(project_key, 0),
            "momentum": _project_momentum(item),
            "risk_level": _project_risk_level(item),
            "next_action": _project_next_action(project_name, command_center),
        }
        items.append(enriched)

    items.sort(
        key=lambda item: (
            {"High": 0, "Medium": 1, "Low": 2}.get(item.get("risk_level"), 3),
            -int(item.get("overdue", 0) or 0),
            -int(item.get("today", 0) or 0),
            _key(item.get("project")),
        )
    )

    return items[:limit]


def _memory_context(memories: list[dict[str, Any]], project: str, limit: int) -> dict[str, Any]:
    relevant = _filter_memories(memories, project) if project else [
        memory
        for memory in memories
        if _key(memory.get("importance")) in {"high", "medium"}
        or _key(memory.get("type")) in {"instruction", "preference", "project", "business"}
    ]

    recent = memories[:limit]

    return {
        "relevant_memories": [_slim_memory(memory) for memory in _limited(relevant, limit)],
        "recent_memories": [_slim_memory(memory) for memory in _limited(recent, limit)],
    }


def _blockers(
    command_center: dict[str, list[dict[str, Any]]],
    raw_rollups: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    blockers = []

    overdue = command_center.get("overdue", [])
    if overdue:
        blockers.append(
            {
                "type": "overdue_tasks",
                "severity": "High" if len(overdue) >= 3 else "Medium",
                "description": f"{len(overdue)} overdue task(s) need attention.",
                "suggested_action": "Clear the highest-priority overdue task first.",
            }
        )

    unlinked_tasks = raw_rollups.get("unlinked_tasks", 0)
    if unlinked_tasks:
        blockers.append(
            {
                "type": "unlinked_tasks",
                "severity": "Medium",
                "description": f"{unlinked_tasks} task(s) are not linked to a project.",
                "suggested_action": "Assign unlinked tasks to active projects.",
            }
        )

    no_date = command_center.get("no_date", [])
    if len(no_date) >= 5:
        blockers.append(
            {
                "type": "many_no_date_tasks",
                "severity": "Medium",
                "description": f"{len(no_date)} active task(s) do not have dates.",
                "suggested_action": "Add dates to the most important no-date tasks.",
            }
        )

    active_without_links = raw_rollups.get("active_projects_without_links", [])
    if active_without_links:
        blockers.append(
            {
                "type": "active_projects_without_links",
                "severity": "Low",
                "description": f"{len(active_without_links)} active project(s) have no linked tasks or memories.",
                "suggested_action": "Add one next action or memory to each active project.",
            }
        )

    return blockers[:limit]


def _risks(
    command_center: dict[str, list[dict[str, Any]]],
    project_rollups: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    risks = []

    high_overdue = [
        task
        for task in command_center.get("overdue", [])
        if _priority(task) == "high"
    ]
    if high_overdue:
        risks.append(
            {
                "type": "high_priority_overdue",
                "severity": "Critical",
                "reason": f"{len(high_overdue)} high-priority task(s) are overdue.",
                "suggested_action": "Resolve or reschedule high-priority overdue work.",
            }
        )

    for project in project_rollups:
        if project.get("risk_level") in {"High", "Medium"}:
            risks.append(
                {
                    "type": "project_risk",
                    "project": project.get("project"),
                    "severity": project.get("risk_level"),
                    "reason": "Project has overdue or undated work.",
                    "suggested_action": "Review the project next action.",
                }
            )

    high_decisions_without_project = [
        decision
        for decision in decisions
        if _key(decision.get("importance")) == "high" and not _key(decision.get("project"))
    ]
    if high_decisions_without_project:
        risks.append(
            {
                "type": "unlinked_high_importance_decisions",
                "severity": "Medium",
                "reason": f"{len(high_decisions_without_project)} high-importance decision(s) are not linked to a project.",
                "suggested_action": "Link high-importance decisions to projects.",
            }
        )

    return risks[:limit]


def _counts(command_center: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {
        "today": len(command_center.get("today", [])),
        "overdue": len(command_center.get("overdue", [])),
        "upcoming": len(command_center.get("upcoming", [])),
        "no_date": len(command_center.get("no_date", [])),
        "done": len(command_center.get("done", [])),
    }


def _status_from_counts(counts: dict[str, int], risks: list[dict[str, Any]]) -> str:
    if any(_key(risk.get("severity")) == "critical" for risk in risks):
        return "At Risk"
    if counts["overdue"] >= 5:
        return "Overloaded"
    if counts["overdue"] or counts["no_date"] >= 5:
        return "Needs Attention"
    if counts["today"] == 1 and counts["overdue"] == 0:
        return "Focused"
    return "Clear"


def _headline(counts: dict[str, int], project_rollups: list[dict[str, Any]]) -> str:
    parts = []

    if counts["overdue"]:
        parts.append(f"{counts['overdue']} overdue task(s)")
    if counts["today"]:
        parts.append(f"{counts['today']} task(s) due today")
    if counts["no_date"]:
        parts.append(f"{counts['no_date']} no-date task(s)")

    if not parts:
        parts.append("no urgent task pressure")

    risky_projects = [
        project for project in project_rollups if project.get("risk_level") in {"High", "Medium"}
    ]
    if risky_projects:
        parts.append(f"{len(risky_projects)} project(s) needing attention")

    return "Dashboard shows " + ", ".join(parts) + "."


def _recommendations(
    counts: dict[str, int],
    focus_tasks: list[dict[str, Any]],
    project_rollups: list[dict[str, Any]],
    raw_rollups: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    recommendations = []

    if focus_tasks:
        first = focus_tasks[0]
        recommendations.append(
            {
                "title": "Start with the top focus task",
                "reason": first.get("reason"),
                "suggested_action": first.get("title"),
            }
        )

    if counts["overdue"]:
        recommendations.append(
            {
                "title": "Reduce overdue pressure",
                "reason": f"{counts['overdue']} task(s) are overdue.",
                "suggested_action": "Finish, reschedule, or clarify overdue tasks.",
            }
        )

    risky_projects = [
        project for project in project_rollups if project.get("risk_level") in {"High", "Medium"}
    ]
    if risky_projects:
        project = risky_projects[0]
        recommendations.append(
            {
                "title": f"Review {project.get('project')}",
                "reason": f"Risk level is {project.get('risk_level')}.",
                "suggested_action": (
                    (project.get("next_action") or {}).get("title")
                    or "Define one next action for this project."
                ),
            }
        )

    if raw_rollups.get("unlinked_tasks", 0):
        recommendations.append(
            {
                "title": "Link tasks to projects",
                "reason": f"{raw_rollups.get('unlinked_tasks')} task(s) are unlinked.",
                "suggested_action": "Assign projects to important unlinked tasks.",
            }
        )

    return recommendations[:limit]


def _warnings(raw_rollups: dict[str, Any], decision_warnings: list[str]) -> list[str]:
    warnings = list(decision_warnings or [])

    if raw_rollups.get("unlinked_tasks", 0):
        warnings.append("Some tasks are not linked to a project.")

    if raw_rollups.get("unlinked_memories", 0):
        warnings.append("Some memories are not linked to a project.")

    if raw_rollups.get("unmatched_project_tasks", 0) or raw_rollups.get("unmatched_project_memories", 0):
        warnings.append("Some linked project names do not match a project record.")

    return warnings


def build_unified_dashboard(
    *,
    project: str = "",
    mode: str = "overview",
    limit: int = 10,
    task_repo=None,
    memory_repo=None,
    project_repo=None,
    decision_repo=None,
) -> dict[str, Any]:
    safe_limit = _safe_limit(limit)
    safe_mode = _safe_mode(mode)
    requested_project = _clean(project)

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

    decision_warnings: list[str] = []
    decisions = _decision_search(decision_repo, requested_project, decision_warnings)
    high_decision_projects = _high_decision_projects(decisions)

    raw_rollups = build_project_rollups(
        scoped_tasks,
        scoped_memories,
        scoped_projects,
        command_center,
    )
    project_rollups = _dashboard_project_rollups(
        raw_rollups,
        command_center,
        decisions,
        safe_limit,
    )

    focus_tasks = _rank_focus_tasks(
        command_center,
        high_decision_projects,
        min(safe_limit, 5),
    )
    counts = _counts(command_center)
    blockers = _blockers(command_center, raw_rollups, safe_limit)
    risks = _risks(command_center, project_rollups, decisions, safe_limit)
    dashboard_status = _status_from_counts(counts, risks)
    recommendations = _recommendations(
        counts,
        focus_tasks,
        project_rollups,
        raw_rollups,
        safe_limit,
    )

    return {
        "dry_run": True,
        "writes": False,
        "generated_at": datetime.utcnow().isoformat(),
        "scope": {
            "mode": safe_mode,
            "project": requested_project,
            "limit": safe_limit,
        },
        "summary": {
            "headline": _headline(counts, project_rollups),
            "suggested_first_action": focus_tasks[0] if focus_tasks else None,
            "dashboard_status": dashboard_status,
        },
        "focus": {
            "top_tasks": focus_tasks,
            "reason": "Selected from due date, overdue status, priority, project linkage, urgency, and high-importance decisions.",
        },
        "task_buckets": _bucketed_slim_tasks(command_center, safe_limit),
        "project_rollups": project_rollups,
        "decision_context": {
            "high_importance_decisions": _high_importance_decisions(decisions, safe_limit),
            "linked_decisions": [_slim_decision(decision) for decision in _limited(decisions, safe_limit)],
        },
        "memory_context": _memory_context(scoped_memories, requested_project, safe_limit),
        "blockers": blockers,
        "risks": risks,
        "execution_progress": {
            "completed_count": counts["done"],
            "pending_count": (
                counts["today"]
                + counts["overdue"]
                + counts["upcoming"]
                + counts["no_date"]
            ),
            "overdue_count": counts["overdue"],
            "today_count": counts["today"],
            "project_momentum": [
                {
                    "project": project.get("project"),
                    "momentum": project.get("momentum"),
                    "risk_level": project.get("risk_level"),
                }
                for project in project_rollups
            ],
        },
        "recommendations": recommendations,
        "warnings": _warnings(raw_rollups, decision_warnings),
    }
