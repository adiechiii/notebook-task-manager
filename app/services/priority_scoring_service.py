import re
from datetime import datetime
from typing import Any


URGENCY_PATTERNS = {
    "urgent": r"\burgent\b",
    "asap": r"\basap\b",
    "critical": r"\bcritical\b",
    "important": r"\bimportant\b",
    "deadline": r"\bdeadline\b",
    "today": r"\btoday\b",
    "tomorrow": r"\btomorrow\b",
    "blocked": r"\b(blocked|blocker|blocking)\b",
    "dependency": r"\b(dependency|depends on|waiting on)\b",
    "stuck": r"\bstuck\b",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    return " ".join(_clean(value).lower().split())


def _priority_points(value: Any) -> tuple[int, str | None]:
    priority = _key(value)

    if priority == "high":
        return 18, "Manual priority is High."
    if priority == "medium":
        return 9, "Manual priority is Medium."
    if priority == "low":
        return 2, "Manual priority is Low."

    return 0, None


def _importance_points(value: Any, label: str) -> tuple[int, str | None]:
    importance = _key(value)

    if importance == "high":
        return 18, f"{label} is High importance."
    if importance == "medium":
        return 9, f"{label} is Medium importance."
    if importance == "low":
        return 2, f"{label} is Low importance."

    return 0, None


def _parse_date(value: Any):
    cleaned = _clean(value)
    if not cleaned:
        return None

    try:
        return datetime.fromisoformat(cleaned).date()
    except ValueError:
        return None


def _due_date_points(due_date: Any, task_context: dict[str, Any]) -> tuple[int, list[str]]:
    bucket = _key((task_context or {}).get("bucket"))
    parsed_due = _parse_date(due_date)
    today = datetime.utcnow().date()

    if bucket == "overdue":
        if parsed_due:
            days = max((today - parsed_due).days, 1)
            return min(40 + days, 55), [f"Item is overdue by {days} day(s)."]
        return 40, ["Item is overdue."]

    if bucket == "today":
        return 35, ["Item is due today."]

    if parsed_due:
        days_until = (parsed_due - today).days
        if days_until < 0:
            return min(40 + abs(days_until), 55), [f"Item is overdue by {abs(days_until)} day(s)."]
        if days_until == 0:
            return 35, ["Item is due today."]
        if days_until <= 3:
            return 25, [f"Item is due in {days_until} day(s)."]
        if days_until <= 7:
            return 14, [f"Item is due within {days_until} day(s)."]
        return 5, ["Item has an upcoming due date."]

    return 0, []


def _urgency_points(text: str) -> tuple[int, list[str], list[str]]:
    lowered = _key(text)
    matched = []

    for label, pattern in URGENCY_PATTERNS.items():
        if re.search(pattern, lowered):
            matched.append(label)

    points = min(len(matched) * 6, 24)
    reasons = [f"Contains urgency indicator: {label}." for label in matched]

    return points, reasons, matched


def _decision_points(related_decisions: list[dict[str, Any]]) -> tuple[int, list[str]]:
    points = 0
    reasons = []

    for decision in related_decisions or []:
        decision_points, reason = _importance_points(
            decision.get("importance"),
            "Related decision",
        )
        if decision_points:
            points += decision_points
            if reason:
                decision_text = _clean(decision.get("decision"))
                if decision_text:
                    reasons.append(f"{reason} Decision: {decision_text[:120]}")
                else:
                    reasons.append(reason)

    return min(points, 35), reasons[:3]


def _memory_points(related_memories: list[dict[str, Any]]) -> tuple[int, list[str]]:
    if not related_memories:
        return 0, []

    points = 0
    reasons = []

    for memory in related_memories[:3]:
        relevance = int(memory.get("relevance_score", 0) or 0)
        points += min(max(relevance // 10, 1), 8)
        summary = _clean(memory.get("summary") or memory.get("text"))
        if summary:
            reasons.append(f"Related memory: {summary[:120]}")

    return min(points, 18), reasons


def _blocker_points(text: str) -> tuple[int, list[str]]:
    lowered = _key(text)
    if re.search(r"\b(blocked|blocker|blocking|stuck|waiting on|depends on|dependency)\b", lowered):
        return 14, ["Blocker or dependency language detected."]
    return 0, []


def _band(score: int) -> str:
    if score >= 85:
        return "critical"
    if score >= 60:
        return "high"
    if score >= 35:
        return "medium"
    return "low"


def _priority_from_score(score: int) -> str:
    if score >= 60:
        return "High"
    if score >= 35:
        return "Medium"
    return "Low"


def score_priority(
    text: str,
    manual_priority: str = "",
    due_date: str = "",
    project: str = "",
    project_metadata: dict[str, Any] | None = None,
    related_decisions: list[dict[str, Any]] | None = None,
    related_memories: list[dict[str, Any]] | None = None,
    task_context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    project_metadata = project_metadata or {}
    task_context = task_context or {}

    score_breakdown = {
        "due_date": 0,
        "urgency": 0,
        "manual_priority": 0,
        "project_importance": 0,
        "decision_importance": 0,
        "blocker_risk": 0,
        "memory_relevance": 0,
        "project_linkage": 0,
    }
    reasons = []

    due_points, due_reasons = _due_date_points(due_date, task_context)
    score_breakdown["due_date"] = due_points
    reasons.extend(due_reasons)

    urgency_points, urgency_reasons, urgency_matches = _urgency_points(text)
    score_breakdown["urgency"] = urgency_points
    reasons.extend(urgency_reasons)

    manual_points, manual_reason = _priority_points(manual_priority)
    score_breakdown["manual_priority"] = manual_points
    if manual_reason:
        reasons.append(manual_reason)

    project_points, project_reason = _importance_points(
        project_metadata.get("priority"),
        "Linked project",
    )
    score_breakdown["project_importance"] = project_points
    if project_reason:
        reasons.append(project_reason)

    if _clean(project):
        score_breakdown["project_linkage"] = 5
        reasons.append("Item is linked to a project.")
    else:
        score_breakdown["project_linkage"] = -5
        reasons.append("Item is not linked to a project.")

    decision_points, decision_reasons = _decision_points(related_decisions or [])
    score_breakdown["decision_importance"] = decision_points
    reasons.extend(decision_reasons)

    blocker_points, blocker_reasons = _blocker_points(text)
    score_breakdown["blocker_risk"] = blocker_points
    reasons.extend(blocker_reasons)

    memory_points, memory_reasons = _memory_points(related_memories or [])
    score_breakdown["memory_relevance"] = memory_points
    reasons.extend(memory_reasons)

    score = sum(score_breakdown.values())
    priority_band = _band(score)
    priority = _priority_from_score(score)

    return {
        "priority": priority,
        "priority_band": priority_band,
        "score": score,
        "scoring_reason": (
            " ".join(reasons[:6])
            if reasons
            else "No strong urgency, date, project, decision, or memory signal detected."
        ),
        "score_breakdown": score_breakdown,
        "signals": {
            "matched_urgency_indicators": urgency_matches,
            "has_project": bool(_clean(project)),
            "related_decision_count": len(related_decisions or []),
            "related_memory_count": len(related_memories or []),
        },
    }
