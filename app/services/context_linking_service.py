import re
from typing import Any


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "i", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "we", "will", "with", "you", "your",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    return " ".join(_clean(value).lower().split())


def _tokens(value: Any) -> set[str]:
    words = re.findall(r"[a-z0-9]+", _key(value))
    return {word for word in words if len(word) >= 3 and word not in STOPWORDS}


def _active_project(project: dict[str, Any]) -> bool:
    status = _key(project.get("status"))
    return not status or status == "active"


def _project_name(project: dict[str, Any]) -> str:
    return _clean(project.get("name"))


def _project_text(project: dict[str, Any]) -> str:
    return " ".join(
        [
            _clean(project.get("name")),
            _clean(project.get("description")),
            _clean(project.get("goal")),
            _clean(project.get("category")),
            _clean(project.get("tags")),
            _clean(project.get("priority")),
        ]
    )


def _project_matches(value: Any, project_name: str) -> bool:
    wanted = _key(project_name)
    current = _key(value)

    if not wanted or not current:
        return False

    return current == wanted or wanted in current or current in wanted


def _importance_points(value: Any) -> int:
    priority = _key(value)
    if priority == "high":
        return 8
    if priority == "medium":
        return 4
    if priority == "low":
        return 1
    return 0


def _confidence(score: int) -> str:
    if score >= 80:
        return "high"
    if score >= 50:
        return "medium"
    if score >= 20:
        return "low"
    return "none"


def _related_text_for_project(
    *,
    project_name: str,
    memories: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> str:
    related_parts = []

    for memory in memories or []:
        if _project_matches(memory.get("project"), project_name):
            related_parts.append(
                " ".join(
                    [
                        _clean(memory.get("text")),
                        _clean(memory.get("summary")),
                        _clean(memory.get("tags")),
                        _clean(memory.get("entity")),
                    ]
                )
            )

    for decision in decisions or []:
        if _project_matches(decision.get("project"), project_name):
            related_parts.append(
                " ".join(
                    [
                        _clean(decision.get("decision")),
                        _clean(decision.get("context")),
                        _clean(decision.get("rationale")),
                        _clean(decision.get("tradeoffs")),
                        _clean(decision.get("tags")),
                    ]
                )
            )

    for task in tasks or []:
        if _project_matches(task.get("project"), project_name):
            related_parts.append(
                " ".join(
                    [
                        _clean(task.get("title")),
                        _clean(task.get("text")),
                        _clean(task.get("category")),
                    ]
                )
            )

    return " ".join(related_parts)


def _score_project(
    *,
    text: str,
    text_tokens: set[str],
    project: dict[str, Any],
    memories: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
) -> dict[str, Any]:
    name = _project_name(project)
    project_key = _key(name)
    haystack = _key(text)
    project_tokens = _tokens(_project_text(project))
    overlap = sorted(text_tokens.intersection(project_tokens))
    related_text = _related_text_for_project(
        project_name=name,
        memories=memories,
        decisions=decisions,
        tasks=tasks,
    )
    related_tokens = _tokens(related_text)
    related_overlap = sorted(text_tokens.intersection(related_tokens))

    score = 0
    reasons = []
    signals = {
        "explicit_project": False,
        "project_name_match": False,
        "project_text_overlap": False,
        "tag_overlap": False,
        "memory_decision_task_overlap": False,
        "active_project": _active_project(project),
    }

    if project_key and project_key in haystack:
        score += 55
        signals["project_name_match"] = True
        reasons.append("matched project name")

    if overlap:
        score += min(len(overlap) * 8, 32)
        signals["project_text_overlap"] = True
        reasons.append("project text overlap: " + ", ".join(overlap[:6]))

    tag_overlap = sorted(text_tokens.intersection(_tokens(project.get("tags"))))
    if tag_overlap:
        score += min(len(tag_overlap) * 10, 25)
        signals["tag_overlap"] = True
        reasons.append("tag overlap: " + ", ".join(tag_overlap[:4]))

    if related_overlap:
        score += min(len(related_overlap) * 6, 24)
        signals["memory_decision_task_overlap"] = True
        reasons.append("related context overlap: " + ", ".join(related_overlap[:6]))

    score += _importance_points(project.get("priority"))

    if not _active_project(project):
        score -= 30
        reasons.append("project is not active")

    return {
        "project": name,
        "score": max(score, 0),
        "linking_reason": "; ".join(reasons) if reasons else "No strong project signal.",
        "signals": signals,
    }


def suggest_project_link(
    text: str,
    explicit_project: str = "",
    projects: list[dict[str, Any]] | None = None,
    memories: list[dict[str, Any]] | None = None,
    decisions: list[dict[str, Any]] | None = None,
    tasks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    explicit = _clean(explicit_project)
    if explicit:
        return {
            "suggested_project": explicit,
            "confidence": "high",
            "score": 100,
            "linking_reason": "Explicit project was provided.",
            "signals": {
                "explicit_project": True,
                "project_name_match": False,
                "project_text_overlap": False,
                "tag_overlap": False,
                "memory_decision_task_overlap": False,
                "active_project": True,
            },
            "candidate_projects": [],
        }

    text_tokens = _tokens(text)
    if not text_tokens:
        return {
            "suggested_project": "",
            "confidence": "none",
            "score": 0,
            "linking_reason": "No text available for project linking.",
            "signals": {},
            "candidate_projects": [],
        }

    candidates = []
    for project in projects or []:
        if not _project_name(project):
            continue

        scored = _score_project(
            text=text,
            text_tokens=text_tokens,
            project=project,
            memories=memories or [],
            decisions=decisions or [],
            tasks=tasks or [],
        )
        if scored["score"] > 0:
            candidates.append(scored)

    candidates.sort(
        key=lambda item: (
            -int(item.get("score", 0) or 0),
            _key(item.get("project")),
        )
    )

    best = candidates[0] if candidates else None
    if not best:
        return {
            "suggested_project": "",
            "confidence": "none",
            "score": 0,
            "linking_reason": "No matching project signal found.",
            "signals": {},
            "candidate_projects": [],
        }

    return {
        "suggested_project": best["project"],
        "confidence": _confidence(int(best["score"])),
        "score": best["score"],
        "linking_reason": best["linking_reason"],
        "signals": best["signals"],
        "candidate_projects": candidates[:5],
    }


def resolve_suggested_project(linking_result: dict[str, Any]) -> str:
    if _key(linking_result.get("confidence")) in {"high", "medium"}:
        return _clean(linking_result.get("suggested_project"))
    return ""
