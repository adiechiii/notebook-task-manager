import re
from typing import Any


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "i", "in", "is", "it", "of", "on", "or", "that", "the", "this",
    "to", "we", "will", "with", "you", "your",
}

STRATEGIC_MEMORY_TYPES = {
    "lesson",
    "preference",
    "strategy",
    "insight",
    "client",
    "customer",
}


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _key(value: Any) -> str:
    return " ".join(_clean(value).lower().split())


def _tokens(value: Any) -> set[str]:
    words = re.findall(r"[a-z0-9]+", _key(value))
    return {word for word in words if len(word) >= 3 and word not in STOPWORDS}


def _importance_points(value: Any) -> int:
    importance = _key(value)
    if importance == "high":
        return 15
    if importance == "medium":
        return 8
    if importance == "low":
        return 2
    return 0


def _memory_text(memory: dict[str, Any]) -> str:
    return " ".join(
        [
            _clean(memory.get("text")),
            _clean(memory.get("summary")),
            _clean(memory.get("type")),
            _clean(memory.get("entity")),
            _clean(memory.get("project")),
            _clean(memory.get("tags")),
        ]
    )


def _project_matches(memory_project: Any, project: str) -> bool:
    wanted = _key(project)
    current = _key(memory_project)

    if not wanted or not current:
        return False

    return current == wanted or wanted in current or current in wanted


def _memory_relevance(
    *,
    text_tokens: set[str],
    memory: dict[str, Any],
    project: str,
) -> dict[str, Any]:
    memory_tokens = _tokens(_memory_text(memory))
    overlap = sorted(text_tokens.intersection(memory_tokens))
    score = 0
    reasons = []

    if overlap:
        score += min(len(overlap) * 8, 40)
        reasons.append("keyword overlap: " + ", ".join(overlap[:6]))

    if _project_matches(memory.get("project"), project):
        score += 25
        reasons.append("same project")

    tags = _tokens(memory.get("tags"))
    tag_overlap = sorted(text_tokens.intersection(tags))
    if tag_overlap:
        score += min(len(tag_overlap) * 10, 20)
        reasons.append("tag overlap: " + ", ".join(tag_overlap[:4]))

    entity_tokens = _tokens(memory.get("entity"))
    entity_overlap = sorted(text_tokens.intersection(entity_tokens))
    if entity_overlap:
        score += 10
        reasons.append("entity overlap: " + ", ".join(entity_overlap[:3]))

    score += _importance_points(memory.get("importance"))
    if _importance_points(memory.get("importance")):
        reasons.append(f"{_clean(memory.get('importance'))} importance")

    memory_type = _key(memory.get("type"))
    if memory_type in STRATEGIC_MEMORY_TYPES:
        score += 8
        reasons.append(f"strategic memory type: {memory_type}")

    if _key(memory.get("status")) == "active":
        score += 5

    return {
        "memory": memory,
        "score": score,
        "reasons": reasons,
    }


def find_related_memories(
    text: str,
    project: str = "",
    memories: list[dict[str, Any]] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    text_tokens = _tokens(text)
    if not text_tokens:
        return []

    candidates = []
    for memory in memories or []:
        if _key(memory.get("status")) and _key(memory.get("status")) != "active":
            continue

        relevance = _memory_relevance(
            text_tokens=text_tokens,
            memory=memory,
            project=project,
        )

        if relevance["score"] <= 0:
            continue

        raw_memory = relevance["memory"]
        candidates.append(
            {
                "text": raw_memory.get("text") or raw_memory.get("summary"),
                "summary": raw_memory.get("summary") or raw_memory.get("text"),
                "type": raw_memory.get("type"),
                "entity": raw_memory.get("entity"),
                "project": raw_memory.get("project"),
                "tags": raw_memory.get("tags"),
                "importance": raw_memory.get("importance"),
                "relevance_score": relevance["score"],
                "relevance_reason": (
                    "; ".join(relevance["reasons"])
                    if relevance["reasons"]
                    else "Related by available memory context."
                ),
            }
        )

    candidates.sort(
        key=lambda item: (
            -int(item.get("relevance_score", 0) or 0),
            _key(item.get("summary") or item.get("text")),
        )
    )

    safe_limit = min(max(int(limit or 5), 1), 10)
    return candidates[:safe_limit]
