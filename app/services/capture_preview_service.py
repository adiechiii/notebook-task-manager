import re
from typing import Any

from app.services.category_service import classify_category
from app.services.date_parser_service import normalize_task_title, parse_date_from_text
from app.services.memory_classification_service import classify_memory
from app.services.priority_service import parse_priority_from_text
from app.services.project_linking_service import resolve_project


def _clean(value: str) -> str:
    return str(value or "").strip()


def _lower(value: str) -> str:
    return _clean(value).lower()


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


def _task_preview(text: str, resolved_project: str) -> dict[str, Any]:
    return {
        "raw_text": text,
        "normalized_title": normalize_task_title(text),
        "page_date": parse_date_from_text(text),
        "category": classify_category(text),
        "priority": parse_priority_from_text(text),
        "project": resolved_project,
    }


def _memory_preview(text: str, resolved_project: str) -> dict[str, Any]:
    classification = classify_memory(text)
    if resolved_project:
        classification["project"] = resolved_project

    return {
        "text": text,
        "classification": classification,
    }


def _decision_preview(
    text: str,
    resolved_project: str,
    source_type: str,
    capture_source: str,
) -> dict[str, Any]:
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
        "importance": parse_priority_from_text(text) or "Medium",
        "source_type": source_type or "text",
        "capture_source": capture_source or "manual",
        "created_at": None,
        "updated_at": None,
    }


def preview_capture(
    *,
    text: str,
    project: str = "",
    source_type: str = "text",
    capture_source: str = "manual",
) -> dict[str, Any]:
    cleaned_text = _clean(text)
    resolved_project = resolve_project(cleaned_text, project or "")
    recommended_type, confidence, reason = classify_capture_type(cleaned_text)
    warnings: list[str] = []

    if not cleaned_text:
        warnings.append("Text is empty. Nothing can be captured.")

    supported_confirm_endpoint = ""

    if recommended_type == "task":
        preview = _task_preview(cleaned_text, resolved_project)
        supported_confirm_endpoint = "/ingest/confirm"
    elif recommended_type in {"memory", "note", "idea", "reflection"}:
        preview = _memory_preview(cleaned_text, resolved_project)
        supported_confirm_endpoint = "/memory/create"
    elif recommended_type == "decision":
        preview = _decision_preview(
            cleaned_text,
            resolved_project,
            source_type,
            capture_source,
        )
        supported_confirm_endpoint = "/decisions/create"
    else:
        preview = {
            "text": cleaned_text,
            "project": resolved_project,
            "type": recommended_type,
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
