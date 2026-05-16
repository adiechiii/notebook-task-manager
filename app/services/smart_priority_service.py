import re
from datetime import datetime
from typing import Any

from app.repositories.sheets_decision_repository import SheetsDecisionRepository
from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.repositories.sheets_task_repository import SheetsTaskRepository
from app.services.command_center_service import build_command_center
from app.services.project_rollup_service import build_project_rollups


URGENCY_PATTERNS = {
    "urgent": r"\burgent\b",
    "asap": r"\basap\b",
    "critical": r"\bcritical\b",
    "important": r"\bimportant\b",
    "deadline": r"\bdeadline\b",
    "today": r"\btoday\b",
    "tomorrow": r"\btomorrow\b",
    "blocked": r"\b(blocked|blocker|blocking)\b",
    "risk": r"\b(risk|risky)\b",
    "stuck": r"\bstuck\b",
}

ACTIVE_STATUSES_TO_SKIP = {"done", "archived"}


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


def _is_active_task(task: dict[str, Any]) -> bool:
    return _key(task.get("status")) not in ACTIVE_STATUSES_TO_SKIP


def _date_from_task(task: dict[str, Any]):
    value = _clean(task.get("page_date"))
    if not value:
        return None

    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _priority_points(priority: Any) -> tuple[int, str | None]:
    value = _key(priority)

    if value == "high":
        return 25, "Manual priority is High."
    if value == "medium":
        return 12, "Manual priority is Medium."
    if value == "low":
        return 3, "Manual priority is Low."

    return 0, None


def _importance_points(value: Any) -> tuple[int, str | None]:
    importance = _key(value)

    if importance == "high":
        return 18, "Linked project is High priority."
    if importance == "medium":
        return 9, "Linked project is Medium priority."
    if importance == "low":
        return 2, "Linked project is Low priority."

    return 0, None


def _bucket_lookup(command_center: dict[str, list[dict[str, Any]]]) -> dict[int, str]:
    lookup = {}

    for bucket, tasks in (command_center or {}).items():
        for task in tasks or []:
            lookup[id(task)] = bucket

    return lookup


def _bucket_for_task(task: dict[str, Any], bucket_lookup: dict[int, str]) -> str:
    bucket = bucket_lookup.get(id(task))
    if bucket:
        return bucket

    if _key(task.get("status")) == "done":
        return "done"

    if _date_from_task(task):
        return "upcoming"

    return "no_date"


def _due_date_points(task: dict[str, Any], bucket: str) -> tuple[int, list[str]]:
    due_date = _date_from_task(task)
    today = datetime.utcnow().date()

    if bucket == "overdue":
        points = 40
        if due_date:
            days_overdue = max((today - due_date).days, 1)
            points += min(days_overdue, 10)
            return points, [f"Task is overdue by {days_overdue} day(s)."]
        return points, ["Task is overdue."]

    if bucket == "today":
        return 35, ["Task is due today."]

    if bucket == "upcoming" and due_date:
        days_until_due = (due_date - today).days
        if days_until_due <= 3:
            return 22, [f"Task is due in {days_until_due} day(s)."]
        if days_until_due <= 7:
            return 12, [f"Task is due within {days_until_due} day(s)."]
        return 4, ["Task has an upcoming due date."]

    if bucket == "no_date":
        return -5, ["Task has no due date, so date urgency is lower."]

    return 0, []


def _urgency_points(task: dict[str, Any]) -> tuple[int, list[str], list[str]]:
    text = _key(f"{task.get('title', '')} {task.get('text', '')}")
    matches = []

    for label, pattern in URGENCY_PATTERNS.items():
        if re.search(pattern, text):
            matches.append(label)

    points = min(len(matches) * 5, 20)
    reasons = [f"Contains urgency indicator: {label}." for label in matches]

    return points, reasons, matches


def _repeated_task_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for task in tasks:
        title_key = _key(task.get("title") or task.get("text"))
        if title_key:
            counts[title_key] = counts.get(title_key, 0) + 1

    return counts


def _project_task_counts(tasks: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}

    for task in tasks:
        project_key = _key(task.get("project"))
        if project_key:
            counts[project_key] = counts.get(project_key, 0) + 1

    return counts


def _decision_search(decision_repo, project: str, warnings: list[str]) -> list[dict[str, Any]]:
    try:
        result = decision_repo.search_decisions(project=project or "", limit=100)
    except Exception:
        warnings.append("Decision search failed; smart priorities returned without decision context.")
        return []

    warnings.extend(result.get("warnings", []))
    return result.get("decisions", [])


def _high_decision_projects(decisions: list[dict[str, Any]]) -> set[str]:
    return {
        _key(decision.get("project"))
        for decision in decisions
        if _key(decision.get("importance")) == "high" and _key(decision.get("project"))
    }


def _medium_decision_projects(decisions: list[dict[str, Any]]) -> set[str]:
    return {
        _key(decision.get("project"))
        for decision in decisions
        if _key(decision.get("importance")) == "medium" and _key(decision.get("project"))
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


def _project_metadata(projects: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    metadata = {}

    for project in projects or []:
        project_key = _key(project.get("name"))
        if not project_key:
            continue

        metadata[project_key] = {
            "name": project.get("name"),
            "status": project.get("status"),
            "priority": project.get("priority"),
            "category": project.get("category"),
            "tags": project.get("tags"),
        }

    return metadata


def _project_rollup_by_key(project_rollups: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = list(project_rollups.get("items", [])) + list(project_rollups.get("unmatched_projects", []))
    return {
        _key(item.get("project")): item
        for item in items
        if _key(item.get("project"))
    }


def _score_task(
    task: dict[str, Any],
    *,
    bucket: str,
    project_metadata: dict[str, dict[str, Any]],
    project_rollups: dict[str, dict[str, Any]],
    high_decision_projects: set[str],
    medium_decision_projects: set[str],
    repeated_counts: dict[str, int],
    project_task_counts: dict[str, int],
) -> dict[str, Any]:
    score_breakdown = {
        "due_date": 0,
        "manual_priority": 0,
        "project_importance": 0,
        "decision_importance": 0,
        "project_linkage": 0,
        "blockers_risks": 0,
        "urgency_indicators": 0,
        "repeated_mentions": 0,
    }
    reasons = []

    due_points, due_reasons = _due_date_points(task, bucket)
    score_breakdown["due_date"] = due_points
    reasons.extend(due_reasons)

    priority_points, priority_reason = _priority_points(task.get("priority"))
    score_breakdown["manual_priority"] = priority_points
    if priority_reason:
        reasons.append(priority_reason)

    project_key = _key(task.get("project"))
    project_info = project_metadata.get(project_key, {})
    project_points, project_reason = _importance_points(project_info.get("priority"))
    score_breakdown["project_importance"] = project_points
    if project_reason:
        reasons.append(project_reason)

    if project_key:
        score_breakdown["project_linkage"] = 5
        reasons.append("Task is linked to a project.")
    else:
        score_breakdown["project_linkage"] = -8
        reasons.append("Task is not linked to a project.")

    if project_key in high_decision_projects:
        score_breakdown["decision_importance"] = 30
        reasons.append("Task is linked to a project with a High-Importance decision.")
    elif project_key in medium_decision_projects:
        score_breakdown["decision_importance"] = 12
        reasons.append("Task is linked to a project with a Medium-Importance decision.")

    rollup = project_rollups.get(project_key, {})
    if bucket == "overdue" and _key(task.get("priority")) == "high":
        score_breakdown["blockers_risks"] += 15
        reasons.append("High-priority overdue work is a critical execution risk.")

    if int(rollup.get("overdue", 0) or 0) >= 2:
        score_breakdown["blockers_risks"] += 12
        reasons.append("Linked project has multiple overdue tasks.")

    if int(rollup.get("no_date", 0) or 0) >= 5:
        score_breakdown["blockers_risks"] += 8
        reasons.append("Linked project has a large no-date backlog.")

    urgency_points, urgency_reasons, urgency_matches = _urgency_points(task)
    score_breakdown["urgency_indicators"] = urgency_points
    reasons.extend(urgency_reasons)

    title_key = _key(task.get("title") or task.get("text"))
    repeated_count = repeated_counts.get(title_key, 0)
    if repeated_count >= 2:
        score_breakdown["repeated_mentions"] += min(repeated_count * 5, 15)
        reasons.append(f"Similar task wording appears {repeated_count} time(s).")

    project_count = project_task_counts.get(project_key, 0)
    if project_key and project_count >= 3:
        score_breakdown["repeated_mentions"] += 5
        reasons.append("Project appears repeatedly across active tasks.")

    smart_score = sum(score_breakdown.values())

    if smart_score >= 90:
        priority_band = "critical"
    elif smart_score >= 65:
        priority_band = "high"
    elif smart_score >= 40:
        priority_band = "medium"
    else:
        priority_band = "low"

    return {
        "task_id": task.get("task_id"),
        "title": task.get("title") or task.get("text"),
        "text": task.get("text"),
        "status": task.get("status"),
        "due_date": task.get("page_date"),
        "bucket": bucket,
        "manual_priority": task.get("priority"),
        "project": task.get("project"),
        "project_priority": project_info.get("priority"),
        "smart_score": smart_score,
        "priority_band": priority_band,
        "score_breakdown": score_breakdown,
        "reasons": reasons or ["Selected from active task list."],
        "matched_urgency_indicators": urgency_matches,
    }


def _blockers(command_center: dict[str, list[dict[str, Any]]], project_rollups: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    blockers = []

    overdue_count = len(command_center.get("overdue", []))
    if overdue_count:
        blockers.append(
            {
                "type": "overdue_tasks",
                "severity": "High" if overdue_count >= 3 else "Medium",
                "description": f"{overdue_count} overdue task(s) need smart priority review.",
            }
        )

    if project_rollups.get("unlinked_tasks", 0):
        blockers.append(
            {
                "type": "unlinked_tasks",
                "severity": "Medium",
                "description": f"{project_rollups.get('unlinked_tasks')} task(s) are not linked to a project.",
            }
        )

    no_date_count = len(command_center.get("no_date", []))
    if no_date_count >= 5:
        blockers.append(
            {
                "type": "no_date_backlog",
                "severity": "Medium",
                "description": f"{no_date_count} active task(s) have no date.",
            }
        )

    return blockers[:limit]


def _risks(command_center: dict[str, list[dict[str, Any]]], decisions: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
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
                "reason": f"{len(high_overdue)} high-priority overdue task(s) exist.",
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
                "reason": f"{len(high_decisions_without_project)} High-Importance decision(s) are not linked to a project.",
            }
        )

    return risks[:limit]


def _summary(ranked_tasks: list[dict[str, Any]], command_center: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    top_task = ranked_tasks[0] if ranked_tasks else None

    return {
        "headline": (
            f"Smart priorities ranked {len(ranked_tasks)} active task(s)."
            if ranked_tasks
            else "Smart priorities found no active tasks to rank."
        ),
        "top_task": top_task,
        "critical_count": sum(1 for task in ranked_tasks if task.get("priority_band") == "critical"),
        "high_count": sum(1 for task in ranked_tasks if task.get("priority_band") == "high"),
        "overdue_count": len(command_center.get("overdue", [])),
        "today_count": len(command_center.get("today", [])),
        "no_date_count": len(command_center.get("no_date", [])),
    }


def build_smart_priorities(
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
    warnings: list[str] = []

    task_repo = task_repo or SheetsTaskRepository()
    memory_repo = memory_repo or SheetsMemoryRepository()
    project_repo = project_repo or SheetsProjectRepository()
    decision_repo = decision_repo or SheetsDecisionRepository()

    all_tasks = task_repo.get_active_tasks_for_duplicate_cleanup()

    try:
        all_memories = memory_repo.search_memories("")
    except Exception:
        all_memories = []
        warnings.append("Memory search failed; smart priorities returned without memory rollup context.")

    try:
        all_projects = project_repo.search_projects("")
    except Exception:
        all_projects = []
        warnings.append("Project search failed; smart priorities returned without project metadata.")

    scoped_tasks = _filter_tasks(all_tasks, requested_project)
    scoped_memories = _filter_memories(all_memories, requested_project)
    scoped_projects = _filter_projects(all_projects, requested_project)

    if requested_project and not scoped_tasks and not scoped_projects:
        warnings.append("Project filter returned no matching active tasks or project records.")

    active_tasks = [task for task in scoped_tasks if _is_active_task(task)]
    command_center = build_command_center(active_tasks)

    decision_warnings: list[str] = []
    decisions = _decision_search(decision_repo, requested_project, decision_warnings)
    warnings.extend(decision_warnings)

    high_decision_projects = _high_decision_projects(decisions)
    medium_decision_projects = _medium_decision_projects(decisions)

    raw_rollups = build_project_rollups(
        active_tasks,
        scoped_memories,
        scoped_projects,
        command_center,
    )

    project_info = _project_metadata(scoped_projects)
    rollups_by_key = _project_rollup_by_key(raw_rollups)
    bucket_lookup = _bucket_lookup(command_center)
    repeated_counts = _repeated_task_counts(active_tasks)
    project_counts = _project_task_counts(active_tasks)

    ranked_tasks = []
    for task in active_tasks:
        ranked_tasks.append(
            _score_task(
                task,
                bucket=_bucket_for_task(task, bucket_lookup),
                project_metadata=project_info,
                project_rollups=rollups_by_key,
                high_decision_projects=high_decision_projects,
                medium_decision_projects=medium_decision_projects,
                repeated_counts=repeated_counts,
                project_task_counts=project_counts,
            )
        )

    ranked_tasks.sort(
        key=lambda task: (
            -int(task.get("smart_score", 0) or 0),
            _key(task.get("title")),
        )
    )

    for index, task in enumerate(ranked_tasks, start=1):
        task["smart_rank"] = index

    limited_ranked_tasks = ranked_tasks[:safe_limit]

    return {
        "dry_run": True,
        "writes": False,
        "generated_at": datetime.utcnow().isoformat(),
        "scope": {
            "project": requested_project,
            "limit": safe_limit,
        },
        "summary": _summary(limited_ranked_tasks, command_center),
        "ranked_tasks": limited_ranked_tasks,
        "decision_context": {
            "high_importance_decisions": [
                _slim_decision(decision)
                for decision in decisions
                if _key(decision.get("importance")) == "high"
            ][:safe_limit],
            "high_importance_decision_projects": sorted(high_decision_projects),
        },
        "project_context": {
            "total_active_tasks_ranked": len(ranked_tasks),
            "unlinked_tasks": raw_rollups.get("unlinked_tasks", 0),
            "unmatched_project_tasks": raw_rollups.get("unmatched_project_tasks", 0),
            "project_rollups": raw_rollups.get("items", [])[:safe_limit],
        },
        "blockers": _blockers(command_center, raw_rollups, safe_limit),
        "risks": _risks(command_center, decisions, safe_limit),
        "signals_used": [
            "due_dates",
            "overdue_status",
            "manual_priority",
            "project_importance",
            "decision_importance",
            "repeated_mentions",
            "urgency_indicators",
            "project_linkage",
            "blockers_and_risks",
        ],
        "future_signals": [
            "dependency_chains",
            "historical_completion_behavior",
        ],
        "warnings": warnings,
    }
