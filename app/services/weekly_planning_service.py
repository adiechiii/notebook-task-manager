from datetime import datetime
from typing import Any

from app.repositories.sheets_decision_repository import SheetsDecisionRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center
from app.services.insight_service import build_insights
from app.services.project_rollup_service import build_project_rollups
from app.services.smart_priority_service import build_smart_priorities
from app.services.unified_review_service import build_unified_review
from app.services.weekly_review_service import build_weekly_review


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
    return [item for item in projects if _project_matches(item.get("name"), project)]


def _limited(items: list[Any], limit: int) -> list[Any]:
    return list(items or [])[:limit]


def _slim_task(task: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": task.get("title") or task.get("text"),
        "text": task.get("text"),
        "status": task.get("status"),
        "page_date": task.get("page_date") or task.get("due_date"),
        "category": task.get("category"),
        "priority": task.get("priority") or task.get("manual_priority"),
        "project": task.get("project"),
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


def _decision_search(decision_repo, project: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        result = decision_repo.search_decisions(project=project or "", limit=100)
    except Exception:
        warnings.append("Decision search failed; weekly planning returned without decision follow-up context.")
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


def _focus_areas(
    smart_priorities: dict[str, Any],
    insights: dict[str, Any],
    command_center: dict[str, list[dict[str, Any]]],
    cognition_priorities: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    focus = []

    top_task = (smart_priorities.get("summary") or {}).get("top_task")
    if top_task:
        focus.append(
            {
                "type": "top_priority",
                "title": "Start with the top smart-priority task",
                "reason": "Highest ranked task from Smart Priority Engine.",
                "suggested_action": top_task.get("title"),
                "evidence": top_task,
            }
        )

    for cognition in cognition_priorities:
        evidence = cognition.get("evidence") or {}
        task = evidence.get("task") or {}
        focus.append(
            {
                "type": "cognition_priority",
                "title": cognition.get("title") or "Review cognition priority",
                "reason": cognition.get("description"),
                "suggested_action": task.get("title") or cognition.get("recommended_action"),
                "evidence": evidence,
            }
        )

    for risk in insights.get("risks", []):
        if risk.get("type") == "cognition_priority":
            continue

        focus.append(
            {
                "type": risk.get("type"),
                "title": risk.get("title"),
                "reason": risk.get("description") or risk.get("reason"),
                "suggested_action": risk.get("recommended_action"),
                "evidence": risk.get("evidence"),
            }
        )

    if command_center.get("overdue"):
        focus.append(
            {
                "type": "overdue_cleanup",
                "title": "Reduce overdue pressure",
                "reason": f"{len(command_center.get('overdue', []))} overdue task(s) are active.",
                "suggested_action": "Clear, reschedule, or explicitly defer overdue tasks early in the week.",
                "evidence": [_slim_task(task) for task in command_center.get("overdue", [])[:5]],
            }
        )

    if len(command_center.get("no_date", [])) >= 5:
        focus.append(
            {
                "type": "no_date_triage",
                "title": "Triage no-date tasks",
                "reason": f"{len(command_center.get('no_date', []))} active task(s) have no date.",
                "suggested_action": "Assign dates to the most important no-date tasks.",
                "evidence": [_slim_task(task) for task in command_center.get("no_date", [])[:5]],
            }
        )

    return focus[:limit]


def _priority_tasks(smart_priorities: dict[str, Any], unified_review: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    tasks = []

    for task in smart_priorities.get("ranked_tasks", []):
        tasks.append(
            {
                "title": task.get("title"),
                "project": task.get("project"),
                "bucket": task.get("bucket"),
                "priority_band": task.get("priority_band"),
                "smart_score": task.get("smart_score"),
                "reason": "; ".join(task.get("reasons", [])[:3]),
                "source": "smart_priorities",
                "task": task,
            }
        )

    seen = {_key(task.get("title")) for task in tasks}
    for item in unified_review.get("carryover", []):
        title_key = _key(item.get("title"))
        if not title_key or title_key in seen:
            continue
        tasks.append(
            {
                "title": item.get("title"),
                "project": item.get("project"),
                "bucket": "carryover",
                "priority_band": "medium",
                "smart_score": None,
                "reason": item.get("reason"),
                "source": "unified_review_carryover",
                "task": item,
            }
        )
        seen.add(title_key)

    return tasks[:limit]


def _project_plans(
    project_rollups: dict[str, Any],
    smart_priorities: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    top_tasks_by_project: dict[str, dict[str, Any]] = {}

    for task in smart_priorities.get("ranked_tasks", []):
        project_key = _key(task.get("project"))
        if not project_key or project_key in top_tasks_by_project:
            continue
        top_tasks_by_project[project_key] = task

    plans = []
    items = list(project_rollups.get("items", [])) + list(project_rollups.get("unmatched_projects", []))
    items.sort(
        key=lambda item: (
            -int(item.get("overdue", 0) or 0),
            -int(item.get("today", 0) or 0),
            -int(item.get("no_date", 0) or 0),
            _key(item.get("project")),
        )
    )

    for item in items:
        project_name = item.get("project")
        project_key = _key(project_name)
        top_task = top_tasks_by_project.get(project_key)

        if item.get("task_count", 0) == 0 and item.get("memory_count", 0) == 0:
            continue

        if top_task:
            next_action = top_task.get("title")
            reason = "Top smart-priority task for this project."
        elif item.get("overdue", 0):
            next_action = "Review and resolve overdue project work."
            reason = "Project has overdue tasks."
        elif item.get("no_date", 0):
            next_action = "Assign dates to project tasks without dates."
            reason = "Project has no-date tasks."
        else:
            next_action = "Choose one concrete next action for this project."
            reason = "Project has active context."

        plans.append(
            {
                "project": project_name,
                "priority": item.get("priority"),
                "status": item.get("status"),
                "task_count": item.get("task_count", 0),
                "memory_count": item.get("memory_count", 0),
                "overdue": item.get("overdue", 0),
                "today": item.get("today", 0),
                "upcoming": item.get("upcoming", 0),
                "no_date": item.get("no_date", 0),
                "next_action": next_action,
                "reason": reason,
                "top_task": top_task,
            }
        )

    return plans[:limit]


def _decision_followups(decisions: list[dict[str, Any]], tasks: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    task_projects = {_key(task.get("project")) for task in tasks if _key(task.get("project"))}
    followups = []

    for decision in decisions:
        if _key(decision.get("importance")) != "high":
            continue

        project_key = _key(decision.get("project"))
        if not project_key:
            reason = "High-importance decision has no linked project."
            suggested_action = "Link this decision to a project."
        elif project_key not in task_projects:
            reason = "High-importance decision has no clearly linked active task."
            suggested_action = "Create or link one weekly execution task."
        else:
            reason = "High-importance decision has active execution context."
            suggested_action = "Review whether the linked task still advances this decision."

        item = _slim_decision(decision)
        item["reason"] = reason
        item["suggested_action"] = suggested_action
        followups.append(item)

    return followups[:limit]


def _cognition_priorities(insights: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    from_evidence = ((insights.get("evidence") or {}).get("cognition_priorities") or [])
    from_insights = [
        item
        for item in insights.get("insights", [])
        if item.get("type") == "cognition_priority"
    ]

    combined = []
    seen = set()

    for item in list(from_evidence) + list(from_insights):
        evidence = item.get("evidence") or {}
        task = evidence.get("task") or {}
        key = _key(
            " ".join(
                [
                    str(item.get("type") or ""),
                    str(task.get("title") or task.get("text") or ""),
                    str(task.get("project") or ""),
                ]
            )
        )
        if not key or key in seen:
            continue

        combined.append(item)
        seen.add(key)

    return combined[:limit]


def _weekly_plan(
    counts: dict[str, int],
    priority_tasks: list[dict[str, Any]],
    project_plans: list[dict[str, Any]],
    decision_followups: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    cognition_priorities: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "mode": "dry_run_weekly_plan",
        "start_here": priority_tasks[0] if priority_tasks else None,
        "overdue_cleanup": {
            "count": counts.get("overdue", 0),
            "suggested_action": (
                "Reserve the first planning block for overdue cleanup."
                if counts.get("overdue", 0)
                else "No overdue cleanup needed."
            ),
        },
        "no_date_triage": {
            "count": counts.get("no_date", 0),
            "suggested_action": (
                "Assign dates or intentionally defer the no-date backlog."
                if counts.get("no_date", 0)
                else "No no-date triage needed."
            ),
        },
        "project_execution": {
            "project_count": len(project_plans),
            "suggested_action": "Pick one next action for each active project with current task or memory context.",
        },
        "decision_alignment": {
            "followup_count": len(decision_followups),
            "suggested_action": "Make sure high-importance decisions have project links and active execution tasks.",
        },
        "risk_management": {
            "risk_count": len(risks),
            "suggested_action": (
                "Resolve Critical and High risks before adding new weekly commitments."
                if risks
                else "No major risks detected."
            ),
        },
        "cognition_context": {
            "priority_count": len(cognition_priorities),
            "suggested_action": (
                "Use cognition priority evidence when choosing weekly focus blocks."
                if cognition_priorities
                else "No cognition priority evidence detected."
            ),
        },
    }


def _summary(
    counts: dict[str, int],
    priority_tasks: list[dict[str, Any]],
    risks: list[dict[str, Any]],
    project_plans: list[dict[str, Any]],
) -> dict[str, Any]:
    if risks:
        planning_status = "At Risk" if any(_key(risk.get("severity")) == "critical" for risk in risks) else "Needs Attention"
    elif counts.get("overdue", 0) or counts.get("no_date", 0) >= 5:
        planning_status = "Needs Cleanup"
    else:
        planning_status = "Clear"

    return {
        "headline": (
            f"Weekly planning found {counts.get('overdue', 0)} overdue task(s), "
            f"{counts.get('no_date', 0)} no-date task(s), "
            f"{len(priority_tasks)} priority task(s), and "
            f"{len(project_plans)} project plan(s)."
        ),
        "planning_status": planning_status,
        "suggested_first_action": priority_tasks[0] if priority_tasks else None,
    }


def _warnings(
    project_rollups: dict[str, Any],
    smart_priorities: dict[str, Any],
    insights: dict[str, Any],
    unified_review: dict[str, Any],
    decision_warnings: list[str],
    project: str,
    tasks: list[dict[str, Any]],
    projects: list[dict[str, Any]],
) -> list[str]:
    warnings = []
    warnings.extend(decision_warnings or [])
    warnings.extend(smart_priorities.get("warnings", []) or [])
    warnings.extend(insights.get("warnings", []) or [])
    warnings.extend(unified_review.get("warnings", []) or [])

    if project and not tasks and not projects:
        warnings.append("Project filter returned no matching tasks or project records.")

    if project_rollups.get("unmatched_project_tasks", 0) or project_rollups.get("unmatched_project_memories", 0):
        warnings.append("Some linked project names do not match a project record.")

    deduped = []
    seen = set()
    for warning in warnings:
        key = _key(warning)
        if not key or key in seen:
            continue
        deduped.append(warning)
        seen.add(key)

    return deduped


def build_weekly_planning(
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
    counts = _counts(command_center)
    project_rollups = build_project_rollups(
        scoped_tasks,
        scoped_memories,
        scoped_projects,
        command_center,
    )

    decision_warnings: list[str] = []
    decisions = _decision_search(decision_repo, requested_project, decision_warnings)

    smart_priorities = build_smart_priorities(
        project=requested_project,
        limit=safe_limit,
        task_repo=task_repo,
        memory_repo=memory_repo,
        project_repo=project_repo,
        decision_repo=decision_repo,
    )
    insights = build_insights(
        project=requested_project,
        limit=safe_limit,
        task_repo=task_repo,
        memory_repo=memory_repo,
        project_repo=project_repo,
        decision_repo=decision_repo,
    )
    unified_review = build_unified_review(
        period="weekly",
        project=requested_project,
        limit=safe_limit,
        task_repo=task_repo,
        memory_repo=memory_repo,
        project_repo=project_repo,
        decision_repo=decision_repo,
    )
    weekly_review = build_weekly_review(
        task_repo=task_repo,
        memory_repo=memory_repo,
        project_repo=project_repo,
    )

    priority_tasks = _priority_tasks(smart_priorities, unified_review, safe_limit)
    project_plans = _project_plans(project_rollups, smart_priorities, safe_limit)
    decision_followups = _decision_followups(decisions, scoped_tasks, safe_limit)
    risks = insights.get("risks", [])[:safe_limit]
    cognition_priorities = _cognition_priorities(insights, safe_limit)
    focus_areas = _focus_areas(
        smart_priorities,
        insights,
        command_center,
        cognition_priorities,
        safe_limit,
    )
    recommended_actions = _limited(
        insights.get("recommended_actions", []) + unified_review.get("recommended_focus", []),
        safe_limit,
    )

    return {
        "dry_run": True,
        "writes": False,
        "generated_at": datetime.utcnow().isoformat(),
        "scope": {
            "project": requested_project,
            "limit": safe_limit,
        },
        "summary": _summary(counts, priority_tasks, risks, project_plans),
        "weekly_plan": _weekly_plan(
            counts,
            priority_tasks,
            project_plans,
            decision_followups,
            risks,
            cognition_priorities,
        ),
        "focus_areas": focus_areas,
        "priority_tasks": priority_tasks,
        "project_plans": project_plans,
        "decision_followups": decision_followups,
        "risks": risks,
        "cognition_priorities": cognition_priorities,
        "recommended_actions": recommended_actions,
        "evidence": {
            "counts": counts,
            "smart_priority_summary": smart_priorities.get("summary", {}),
            "insights_summary": insights.get("summary", {}),
            "weekly_review_tasks": weekly_review.get("tasks", {}),
            "project_rollups": project_rollups.get("items", [])[:safe_limit],
            "cognition_priorities": cognition_priorities,
            "unlinked_tasks": project_rollups.get("unlinked_tasks", 0),
            "unlinked_memories": project_rollups.get("unlinked_memories", 0),
            "unmatched_project_tasks": project_rollups.get("unmatched_project_tasks", 0),
            "unmatched_project_memories": project_rollups.get("unmatched_project_memories", 0),
        },
        "signals_used": [
            "tasks",
            "projects",
            "memories",
            "decisions",
            "smart_priorities",
            "insights",
            "weekly_review",
            "carryover",
            "project_rollups",
            "cognition_priorities",
            "related_memory_relevance",
        ],
        "warnings": _warnings(
            project_rollups,
            smart_priorities,
            insights,
            unified_review,
            decision_warnings,
            requested_project,
            scoped_tasks,
            scoped_projects,
        ),
    }
