import re
from difflib import SequenceMatcher


DUPLICATE_THRESHOLD = 90


def _clean(value):
    return str(value or "").strip().lower()


def _canonical(value):
    text = _clean(value)
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _token_overlap_score(left, right):
    left_tokens = set(left.split())
    right_tokens = set(right.split())

    if not left_tokens or not right_tokens:
        return 0

    overlap = left_tokens.intersection(right_tokens)
    largest = max(len(left_tokens), len(right_tokens))
    return round((len(overlap) / largest) * 100)


def _similarity_score(left, right):
    left_canonical = _canonical(left)
    right_canonical = _canonical(right)

    if not left_canonical or not right_canonical:
        return 0

    sequence_score = round(
        SequenceMatcher(None, left_canonical, right_canonical).ratio() * 100
    )
    token_score = _token_overlap_score(left_canonical, right_canonical)

    return round((sequence_score * 0.75) + (token_score * 0.25))


def _confidence(score):
    if score >= DUPLICATE_THRESHOLD:
        return "high"
    if score >= 75:
        return "medium"
    if score > 0:
        return "low"
    return "none"


def _result(duplicate, reason, match, score, match_type):
    return {
        "duplicate": duplicate,
        "duplicate_reason": reason,
        "duplicate_match": match,
        "duplicate_score": score,
        "duplicate_confidence": _confidence(score),
        "duplicate_match_type": match_type,
    }


def find_duplicate_task(parsed_task, existing_tasks):
    raw_text = _clean(parsed_task.get("raw_text"))
    normalized_title = _clean(parsed_task.get("normalized_title"))
    best_match = _result(False, "", "", 0, "")

    for task in existing_tasks:
        existing_raw = _clean(task.get("Raw Text"))
        existing_title = _clean(task.get("Normalized Title"))

        if raw_text and raw_text == existing_raw:
            return _result(
                True,
                "Raw Text match",
                task.get("Raw Text"),
                100,
                "raw_text_exact",
            )

        if normalized_title and normalized_title == existing_title:
            return _result(
                True,
                "Normalized Title match",
                task.get("Raw Text"),
                95,
                "normalized_title_exact",
            )

        score = _similarity_score(normalized_title, existing_title)
        if score > best_match["duplicate_score"]:
            best_match = _result(
                score >= DUPLICATE_THRESHOLD,
                "Title similarity match" if score >= DUPLICATE_THRESHOLD else "",
                task.get("Raw Text") if score >= DUPLICATE_THRESHOLD else "",
                score,
                "title_similarity" if score > 0 else "",
            )

    return best_match


def is_duplicate(text, category, existing_tasks):
    parsed_task = {
        "raw_text": text,
        "normalized_title": text,
        "category": category,
    }

    result = find_duplicate_task(parsed_task, existing_tasks)
    return result["duplicate"]
