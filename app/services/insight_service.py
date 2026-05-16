from datetime import datetime
from typing import Any

from app.repositories.sheets_decision_repository import SheetsDecisionRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center
from app.services.project_rollup_service import build_project_rollups


SEVERITY_RANK = {
    "Critical": 0,
    "High": 1,
    "Medium": 2,
    "Low": 3,
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    return " ".join(_clean(value).lower().split())


def _safe_limit(value: int | None) -> int:
    try:
        limit = int(value or 10)
    except (TypeError, ValueError):
        limit = 10

    return min(max(limit, 1), 50)


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
    return [project_item for project_item in projects if _project_matches(project_item.get("name"), project)]


def _task_title(task: dict[str, Any]) -> str:
    return _clean(task.get("title") or task.get("text"))


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


def _decision_search(decision_repo, project: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        result = decision_repo.search_decisions(project=project or "", limit=100)
    except Exception:
        warnings.append("Decision search failed; insights returned without decision context.")
        return []

    warnings.extend(result.get("warnings", []))
    return result.get("decisions", [])


def _counts(command_center: dict[str, list[dict[str, Any]]]) -> dict[str, int]:
    return {
        "today": len(command_center.get("today", [])),
        "overdue": len(command_center.get("overdue", [])),
        "upcoming": len(command_center.get("upcoming", [])),
        "no_date": len(command_center.get("no_date", [])),
        "done": len(command_center.get("done", [])),
    }


def _high_priority_overdue(command_center: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    return [
        task
        for task in command_center.get("overdue", [])
        if _key(task.get("priority")) == "high"
    ]


def _high_importance_decisions(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        decision
        for decision in decisions
        if _key(decision.get("importance")) == "high"
    ]


def _high_decisions_without_project(decisions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        decision
        for decision in _high_importance_decisions(decisions)
        if not _key(decision.get("project"))
    ]


def _high_decisions_without_active_task(decisions: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    task_projects = {_key(task.get("project")) for task in tasks if _key(task.get("project"))}
    missing = []

    for decision in _high_importance_decisions(decisions):
        project_key = _key(decision.get("project"))
        if project_key and project_key not in task_projects:
            missing.append(decision)

    return missing


def _project_risk_level(rollup: dict[str, Any]) -> str:
    overdue = int(rollup.get("overdue", 0) or 0)
    no_date = int(rollup.get("no_date", 0) or 0)

    if overdue >= 3:
        return "High"
    if overdue or no_date >= 5:
        return "Medium"
    return "Low"


def _project_risks(project_rollups: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    risks = []

    for item in project_rollups.get("items", []):
        severity = _project_risk_level(item)
        if severity == "Low":
            continue

        risks.append(
            {
                "type": "project_risk",
                "severity": severity,
                "title": f"{item.get('project')} needs attention",
                "description": "Project has overdue or undated work.",
                "evidence": {
                    "project": item.get("project"),
                    "overdue": item.get("overdue", 0),
                    "no_date": item.get("no_date", 0),
                    "task_count": item.get("task_count", 0),
                },
                "recommended_action": "Review the project and define the next concrete action.",
            }
        )

    return _sort_insights(risks)[:limit]


def _sort_insights(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        items,
        key=lambda item: (
            SEVERITY_RANK.get(item.get("severity"), 9),
            _key(item.get("title") or item.get("type")),
        ),
    )


def _task_pressure_insights(command_center: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    insights = []
    counts = _counts(command_center)
    high_overdue = _high_priority_overdue(command_center)

    if high_overdue:
        insights.append(
            {
                "type": "task_pressure",
                "severity": "Critical",
                "title": "High-priority overdue work needs immediate attention",
                "description": f"{len(high_overdue)} high-priority overdue task(s) are still open.",
                "evidence": [_slim_task(task) for task in high_overdue[:5]],
                "recommended_action": "Finish, reschedule, or explicitly defer the highest-priority overdue task.",
            }
        )

    if counts["overdue"] >= 5:
        insights.append(
            {
                "type": "overdue_patterns",
                "severity": "High",
                "title": "Overdue task pressure is high",
                "description": f"{counts['overdue']} overdue task(s) are currently active.",
                "evidence": [_slim_task(task) for task in command_center.get("overdue", [])[:5]],
                "recommended_action": "Reduce overdue work before accepting new commitments.",
            }
        )
    elif counts["overdue"]:
        insights.append(
            {
                "type": "overdue_patterns",
                "severity": "Medium",
                "title": "Some overdue work remains",
                "description": f"{counts['overdue']} overdue task(s) need cleanup.",
                "evidence": [_slim_task(task) for task in command_center.get("overdue", [])[:5]],
                "recommended_action": "Clear or reschedule overdue tasks.",
            }
        )

    if counts["no_date"] >= 5:
        insights.append(
            {
                "type": "no_date_backlog",
                "severity": "Medium",
                "title": "No-date backlog is building up",
                "description": f"{counts['no_date']} active task(s) do not have a date.",
                "evidence": [_slim_task(task) for task in command_center.get("no_date", [])[:5]],
                "recommended_action": "Assign dates to the most important no-date tasks.",
            }
        )

    return insights


def _decision_insights(decisions: list[dict[str, Any]], tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    insights = []

    unlinked_high = _high_decisions_without_project(decisions)
    if unlinked_high:
        insights.append(
            {
                "type": "decision_alignment",
                "severity": "Critical",
                "title": "High-importance decisions are not linked to projects",
                "description": f"{len(unlinked_high)} high-importance decision(s) have no project link.",
                "evidence": [_slim_decision(decision) for decision in unlinked_high[:5]],
                "recommended_action": "Link strategic decisions to projects so they can drive execution.",
            }
        )

    missing_execution = _high_decisions_without_active_task(decisions, tasks)
    if missing_execution:
        insights.append(
            {
                "type": "strategic_followup",
                "severity": "High",
                "title": "High-importance decisions may need execution tasks",
                "description": f"{len(missing_execution)} high-importance decision project(s) have no matching active task.",
                "evidence": [_slim_decision(decision) for decision in missing_execution[:5]],
                "recommended_action": "Create or link at least one active task for each strategic decision.",
            }
        )

    return insights


def _memory_insights(memories: list[dict[str, Any]], project_rollups: dict[str, Any]) -> list[dict[str, Any]]:
    insights = []

    important_memories = [
        memory
        for memory in memories
        if _key(memory.get("importance")) == "high"
        or _key(memory.get("type")) in {"instruction", "preference", "project", "business"}
    ]

    if important_memories:
        insights.append(
            {
                "type": "memory_context",
                "severity": "Low",
                "title": "Important memory context is available",
                "description": f"{len(important_memories)} important memory item(s) may affect planning.",
                "evidence": [_slim_memory(memory) for memory in important_memories[:5]],
                "recommended_action": "Use relevant memories when choosing next actions.",
            }
        )

    if project_rollups.get("unlinked_memories", 0):
        insights.append(
            {
                "type": "unlinked_context",
                "severity": "Medium",
                "title": "Some memories are not linked to projects",
                "description": f"{project_rollups.get('unlinked_memories')} memory item(s) are unlinked.",
                "evidence": {
                    "unlinked_memories": project_rollups.get("unlinked_memories", 0),
                },
                "recommended_action": "Link important memories to projects for better context.",
            }
        )

    return insights


def _linkage_insights(project_rollups: dict[str, Any]) -> list[dict[str, Any]]:
    insights = []

    if project_rollups.get("unlinked_tasks", 0):
        insights.append(
            {
                "type": "unlinked_context",
                "severity": "Medium",
                "title": "Some tasks are not linked to projects",
                "description": f"{project_rollups.get('unlinked_tasks')} task(s) are unlinked.",
                "evidence": {
                    "unlinked_tasks": project_rollups.get("unlinked_tasks", 0),
                },
                "recommended_action": "Assign important unlinked tasks to active projects.",
            }
        )

    if project_rollups.get("unmatched_project_tasks", 0) or project_rollups.get("unmatched_project_memories", 0):
        insights.append(
            {
                "type": "unlinked_context",
                "severity": "Medium",
                "title": "Some project links do not match project records",
                "description": "Some task or memory project names do not match an existing project record.",
                "evidence": {
                    "unmatched_project_tasks": project_rollups.get("unmatched_project_tasks", 0),
                    "unmatched_project_memories": project_rollups.get("unmatched_project_memories", 0),
                },
                "recommended_action": "Normalize project names or create the missing project records.",
            }
        )

    active_without_links = project_rollups.get("active_projects_without_links", [])
    if active_without_links:
        insights.append(
            {
                "type": "project_risk",
                "severity": "Medium",
                "title": "Active projects have no linked execution context",
                "description": f"{len(active_without_links)} active project(s) have no linked tasks or memories.",
                "evidence": active_without_links[:5],
                "recommended_action": "Add one next action or memory to each active project.",
            }
        )

    return insights


def _opportunities(command_center: dict[str, list[dict[str, Any]]], project_rollups: dict[str, Any], decisions: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    opportunities = []

    if not command_center.get("today") and command_center.get("overdue"):
        opportunities.append(
            {
                "type": "execution_focus",
                "severity": "Low",
                "title": "Today can be used to reduce overdue pressure",
                "description": "There are no tasks due today, but overdue work exists.",
                "evidence": {
                    "today": 0,
                    "overdue": len(command_center.get("overdue", [])),
                },
                "recommended_action": "Use today to resolve the highest-impact overdue item.",
            }
        )

    high_decision_projects = {
        _key(decision.get("project"))
        for decision in decisions
        if _key(decision.get("importance")) == "high" and _key(decision.get("project"))
    }
    represented_projects = {
        _key(item.get("project"))
        for item in project_rollups.get("items", [])
        if _key(item.get("project"))
    }

    aligned_projects = sorted(high_decision_projects & represented_projects)
    if aligned_projects:
        opportunities.append(
            {
                "type": "decision_alignment",
                "severity": "Low",
                "title": "Execution is connected to high-importance decisions",
                "description": f"{len(aligned_projects)} high-importance decision project(s) have active context.",
                "evidence": {
                    "projects": aligned_projects[:5],
                },
                "recommended_action": "Prioritize the best next action in these strategically important projects.",
            }
        )

    return opportunities[:limit]


def _recommended_actions(insights: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    actions = []

    for insight in _sort_insights(insights):
        action = insight.get("recommended_action")
        if not action:
            continue

        actions.append(
            {
                "source_type": insight.get("type"),
                "severity": insight.get("severity"),
                "title": insight.get("title"),
                "recommended_action": action,
            }
        )

        if len(actions) >= limit:
            break

    return actions


def _overall_status(insights: list[dict[str, Any]]) -> str:
    severities = {_clean(insight.get("severity")) for insight in insights}

    if "Critical" in severities:
        return "At Risk"
    if "High" in severities:
        return "Needs Attention"
    if "Medium" in severities:
        return "Needs Cleanup"
    return "Clear"


def _headline(counts: dict[str, int], insights: list[dict[str, Any]]) -> str:
    if not insights:
        return "Insights show no major risks in the current workspace."

    return (
        f"Insights found {len(insights)} signal(s): "
        f"{counts['overdue']} overdue task(s), "
        f"{counts['no_date']} no-date task(s), and "
        f"{counts['today']} task(s) due today."
    )


def _warnings(project_rollups: dict[str, Any], decision_warnings: list[str], project: str, tasks: list[dict[str, Any]], projects: list[dict[str, Any]]) -> list[str]:
    warnings = list(decision_warnings or [])

    if project and not tasks and not projects:
        warnings.append("Project filter returned no matching tasks or project records.")

    if project_rollups.get("unmatched_project_tasks", 0) or project_rollups.get("unmatched_project_memories", 0):
        warnings.append("Some linked project names do not match a project record.")

    return warnings


def build_insights(
    *,
    project: str = "",
    limit: int = 10,
    task_repo=None,
    memory_repo=None,
    project_repo=None,
    decision_repo=None,
) -> dict[str, Any]:
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

    task_insights = _task_pressure_insights(command_center)
    project_insights = _project_risks(project_rollups, safe_limit)
    decision_insights = _decision_insights(decisions, scoped_tasks)
    memory_insights = _memory_insights(scoped_memories, project_rollups)
    linkage_insights = _linkage_insights(project_rollups)

    insights = _sort_insights(
        task_insights
        + project_insights
        + decision_insights
        + memory_insights
        + linkage_insights
    )
    limited_insights = insights[:safe_limit]
    opportunities = _opportunities(command_center, project_rollups, decisions, safe_limit)
    counts = _counts(command_center)

    return {
        "dry_run": True,
        "writes": False,
        "generated_at": datetime.utcnow().isoformat(),
        "scope": {
            "project": requested_project,
            "limit": safe_limit,
        },
        "summary": {
            "headline": _headline(counts, limited_insights),
            "overall_status": _overall_status(limited_insights),
            "insight_count": len(limited_insights),
            "risk_count": sum(1 for item in limited_insights if item.get("severity") in {"Critical", "High"}),
            "opportunity_count": len(opportunities),
        },
        "insights": limited_insights,
        "patterns": [
            item
            for item in limited_insights
            if item.get("type") in {"overdue_patterns", "no_date_backlog", "unlinked_context"}
        ],
        "risks": [
            item
            for item in limited_insights
            if item.get("severity") in {"Critical", "High"}
        ],
        "opportunities": opportunities,
        "recommended_actions": _recommended_actions(limited_insights + opportunities, safe_limit),
        "evidence": {
            "counts": counts,
            "project_rollups": project_rollups.get("items", [])[:safe_limit],
            "unlinked_tasks": project_rollups.get("unlinked_tasks", 0),
            "unlinked_memories": project_rollups.get("unlinked_memories", 0),
            "unmatched_project_tasks": project_rollups.get("unmatched_project_tasks", 0),
            "unmatched_project_memories": project_rollups.get("unmatched_project_memories", 0),
            "high_importance_decisions": [
                _slim_decision(decision)
                for decision in _high_importance_decisions(decisions)
            ][:safe_limit],
        },
        "signals_used": [
            "task_pressure",
            "project_risk",
            "decision_alignment",
            "memory_context",
            "unlinked_context",
            "overdue_patterns",
            "no_date_backlog",
            "strategic_followup",
            "execution_focus",
        ],
        "future_signals": [
            "dependency_chains",
            "historical_completion_behavior",
            "semantic_memory_clustering",
            "cross-project_goal_alignment",
        ],
        "warnings": _warnings(
            project_rollups,
            decision_warnings,
            requested_project,
            scoped_tasks,
            scoped_projects,
        ),
    }
