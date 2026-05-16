import re
from typing import Any

from app.services.category_service import classify_category
from app.services.context_linking_service import (
    resolve_suggested_project,
    suggest_project_link,
)
from app.services.date_parser_service import normalize_task_title, parse_date_from_text
from app.services.memory_classification_service import classify_memory
from app.services.priority_scoring_service import score_priority
from app.services.priority_service import parse_priority_from_text
from app.services.project_linking_service import resolve_project
from app.services.related_memory_service import find_related_memories


def _clean(value: str) -> str:
    return str(value or "").strip()


def _lower(value: str) -> str:
    return _clean(value).lower()


def _key(value: Any) -> str:
    return " ".join(_clean(value).lower().split())


def _project_matches(value: Any, project: str) -> bool:
    wanted = _key(project)
    current = _key(value)

    if not wanted or not current:
        return False

    return current == wanted or wanted in current or current in wanted


def _looks_like_expense(text: str) -> bool:
    lowered = _lower(text)
    return bool(
        re.search(r"(\$|aed|usd|spent|paid|receipt|expense|cost|invoice)", lowered)
    )


def _looks_like_recurring_request(text: str) -> bool:
    lowered = _lower(text)
    return bool(
        re.search(
            r"\b(every|daily|weekly|monthly|yearly|annually|recurring|repeat)\b",
            lowered,
        )
    )


def _looks_like_decision(text: str) -> bool:
    lowered = _lower(text)
    return bool(
        re.search(
            r"\b(decided|decision|choose|chosen|approved|commit to|we will|i will use|use .* as|focus on|instead of)\b",
            lowered,
        )
    )


def _looks_like_idea(text: str) -> bool:
    lowered = _lower(text)
    return bool(re.search(r"\b(idea|maybe|what if|could|possible|concept)\b", lowered))


def _looks_like_reflection(text: str) -> bool:
    lowered = _lower(text)
    return bool(
        re.search(
            r"\b(reflection|today i learned|i noticed|lesson|worked well|did not work|blocker|stuck)\b",
            lowered,
        )
    )


def _looks_like_memory(text: str) -> bool:
    lowered = _lower(text)
    return bool(
        re.search(
            r"\b(remember|note|always|never|prefers|likes|dislikes|clients?|customers?|should|must|do not|don't)\b",
            lowered,
        )
    )


def _looks_like_task(text: str) -> bool:
    lowered = _lower(text)
    return bool(
        re.search(
            r"\b(todo|task|call|email|follow up|finish|build|send|submit|review|pay|schedule|prepare|create|update|fix|test|deploy|tomorrow|today|due|urgent)\b",
            lowered,
        )
    )


def classify_capture_type(text: str) -> tuple[str, str, str]:
    if _looks_like_expense(text):
        return (
            "expense_request",
            "medium",
            "Detected expense/payment language. Preview only; expense confirm is not implemented yet.",
        )

    if _looks_like_recurring_request(text):
        return (
            "recurring_task_request",
            "medium",
            "Detected recurring schedule language. Preview only; recurring confirm is not implemented yet.",
        )

    if _looks_like_decision(text):
        return (
            "decision",
            "high",
            "Detected decision language such as choice, commitment, focus, or tradeoff.",
        )

    if _looks_like_reflection(text):
        return (
            "reflection",
            "medium",
            "Detected reflection or blocker language.",
        )

    if _looks_like_idea(text):
        return (
            "idea",
            "medium",
            "Detected idea or possibility language.",
        )

    if _looks_like_memory(text):
        return (
            "memory",
            "medium",
            "Detected note, instruction, preference, or memory language.",
        )

    if _looks_like_task(text):
        return (
            "task",
            "high",
            "Detected action-oriented task language.",
        )

    return (
        "note",
        "low",
        "No strong task, decision, memory, idea, reflection, expense, or recurring signal was detected.",
    )


def _load_cognition_context(warnings: list[str]) -> dict[str, list[dict[str, Any]]]:
    projects: list[dict[str, Any]] = []
    memories: list[dict[str, Any]] = []
    decisions: list[dict[str, Any]] = []
    tasks: list[dict[str, Any]] = []

    try:
        from app.repositories.sheets_project_repository import SheetsProjectRepository

        projects = SheetsProjectRepository().search_projects("")
    except Exception:
        warnings.append("Project context could not be loaded for smart linking.")

    try:
        from app.repositories.sheets_memory_repository import SheetsMemoryRepository

        memories = SheetsMemoryRepository().search_memories("")
    except Exception:
        warnings.append("Memory context could not be loaded for related memory suggestions.")

    try:
        from app.repositories.sheets_decision_repository import SheetsDecisionRepository

        decision_result = SheetsDecisionRepository().search_decisions(limit=100)
        decisions = decision_result.get("decisions", [])
        warnings.extend(decision_result.get("warnings", []))
    except Exception:
        warnings.append("Decision context could not be loaded for priority scoring.")

    try:
        from app.repositories.sheets_task_repository import SheetsTaskRepository

        tasks = SheetsTaskRepository().get_active_tasks_for_duplicate_cleanup()
    except Exception:
        warnings.append("Task context could not be loaded for smart linking.")

    return {
        "projects": projects,
        "memories": memories,
        "decisions": decisions,
        "tasks": tasks,
    }


def _project_metadata(projects: list[dict[str, Any]], project: str) -> dict[str, Any]:
    for item in projects or []:
        if _project_matches(item.get("name"), project):
            return item
    return {}


def _related_decisions(
    decisions: list[dict[str, Any]],
    project: str,
    limit: int = 5,
) -> list[dict[str, Any]]:
    if not _clean(project):
        return []

    related = [
        decision
        for decision in decisions or []
        if _project_matches(decision.get("project"), project)
    ]

    related.sort(
        key=lambda item: (
            _key(item.get("importance")) != "high",
            _key(item.get("decision")),
        )
    )
    return related[:limit]


def _cognition_for_capture(
    *,
    text: str,
    explicit_project: str,
    warnings: list[str],
) -> dict[str, Any]:
    context = _load_cognition_context(warnings)
    legacy_project = resolve_project(text, explicit_project or "")

    project_linking = suggest_project_link(
        text=text,
        explicit_project=explicit_project or legacy_project,
        projects=context["projects"],
        memories=context["memories"],
        decisions=context["decisions"],
        tasks=context["tasks"],
    )
    resolved_project = resolve_suggested_project(project_linking) or legacy_project

    related_memories = find_related_memories(
        text=text,
        project=resolved_project,
        memories=context["memories"],
        limit=5,
    )
    related_decisions = _related_decisions(context["decisions"], resolved_project)

    return {
        "resolved_project": resolved_project,
        "project_linking": project_linking,
        "related_memories": related_memories,
        "related_decisions": related_decisions,
        "project_metadata": _project_metadata(context["projects"], resolved_project),
    }


def _task_preview(
    text: str,
    resolved_project: str,
    project_linking: dict[str, Any],
    related_memories: list[dict[str, Any]],
    related_decisions: list[dict[str, Any]],
    project_metadata: dict[str, Any],
) -> dict[str, Any]:
    page_date = parse_date_from_text(text)
    parsed_priority = parse_priority_from_text(text)
    priority_scoring = score_priority(
        text=text,
        manual_priority=parsed_priority,
        due_date=page_date,
        project=resolved_project,
        project_metadata=project_metadata,
        related_decisions=related_decisions,
        related_memories=related_memories,
    )

    return {
        "raw_text": text,
        "normalized_title": normalize_task_title(text),
        "page_date": page_date,
        "category": classify_category(text),
        "priority": priority_scoring.get("priority") or parsed_priority,
        "parsed_priority": parsed_priority,
        "project": resolved_project,
        "suggested_project": project_linking.get("suggested_project", ""),
        "project_linking": project_linking,
        "priority_scoring": priority_scoring,
        "related_memories": related_memories,
    }


def _memory_preview(
    text: str,
    resolved_project: str,
    project_linking: dict[str, Any],
    related_memories: list[dict[str, Any]],
) -> dict[str, Any]:
    classification = classify_memory(text)
    if resolved_project:
        classification["project"] = resolved_project

    return {
        "text": text,
        "classification": classification,
        "suggested_project": project_linking.get("suggested_project", ""),
        "project_linking": project_linking,
        "related_memories": related_memories,
    }


def _decision_preview(
    text: str,
    resolved_project: str,
    source_type: str,
    capture_source: str,
    project_linking: dict[str, Any],
    related_memories: list[dict[str, Any]],
    related_decisions: list[dict[str, Any]],
    project_metadata: dict[str, Any],
) -> dict[str, Any]:
    parsed_importance = parse_priority_from_text(text) or "Medium"
    priority_scoring = score_priority(
        text=text,
        manual_priority=parsed_importance,
        project=resolved_project,
        project_metadata=project_metadata,
        related_decisions=related_decisions,
        related_memories=related_memories,
    )

    return {
        "decision_id": None,
        "decision": text,
        "context": "",
        "rationale": "",
        "outcome": "",
        "tradeoffs": "",
        "project": resolved_project,
        "tags": "",
        "status": "Active",
        "importance": priority_scoring.get("priority") or parsed_importance,
        "parsed_importance": parsed_importance,
        "source_type": source_type or "text",
        "capture_source": capture_source or "manual",
        "created_at": None,
        "updated_at": None,
        "suggested_project": project_linking.get("suggested_project", ""),
        "project_linking": project_linking,
        "priority_scoring": priority_scoring,
        "related_memories": related_memories,
    }


def preview_capture(
    *,
    text: str,
    project: str = "",
    source_type: str = "text",
    capture_source: str = "manual",
) -> dict[str, Any]:
    cleaned_text = _clean(text)
    recommended_type, confidence, reason = classify_capture_type(cleaned_text)
    warnings: list[str] = []

    if not cleaned_text:
        warnings.append("Text is empty. Nothing can be captured.")

    cognition = _cognition_for_capture(
        text=cleaned_text,
        explicit_project=project or "",
        warnings=warnings,
    )
    resolved_project = cognition["resolved_project"]
    project_linking = cognition["project_linking"]
    related_memories = cognition["related_memories"]
    related_decisions = cognition["related_decisions"]
    project_metadata = cognition["project_metadata"]

    supported_confirm_endpoint = ""

    if recommended_type == "task":
        preview = _task_preview(
            cleaned_text,
            resolved_project,
            project_linking,
            related_memories,
            related_decisions,
            project_metadata,
        )
        supported_confirm_endpoint = "/capture/confirm"
    elif recommended_type in {"memory", "note", "idea", "reflection"}:
        preview = _memory_preview(
            cleaned_text,
            resolved_project,
            project_linking,
            related_memories,
        )
        supported_confirm_endpoint = "/capture/confirm"
    elif recommended_type == "decision":
        preview = _decision_preview(
            cleaned_text,
            resolved_project,
            source_type,
            capture_source,
            project_linking,
            related_memories,
            related_decisions,
            project_metadata,
        )
        supported_confirm_endpoint = "/capture/confirm"
    else:
        preview = {
            "text": cleaned_text,
            "project": resolved_project,
            "type": recommended_type,
            "suggested_project": project_linking.get("suggested_project", ""),
            "project_linking": project_linking,
            "related_memories": related_memories,
        }
        warnings.append(
            "This type is preview-only right now. No dedicated confirm endpoint is exposed yet."
        )

    return {
        "dry_run": True,
        "writes": False,
        "recommended_type": recommended_type,
        "confidence": confidence,
        "reason": reason,
        "resolved_project": resolved_project,
        "preview": preview,
        "supported_confirm_endpoint": supported_confirm_endpoint,
        "warnings": warnings,
    }
