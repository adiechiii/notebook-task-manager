def _clean(value):
    return str(value or "").strip().lower()


def find_duplicate_task(parsed_task, existing_tasks):
    raw_text = _clean(parsed_task.get("raw_text"))
    normalized_title = _clean(parsed_task.get("normalized_title"))

    for task in existing_tasks:
        existing_raw = _clean(task.get("Raw Text"))
        existing_title = _clean(task.get("Normalized Title"))

        if raw_text and raw_text == existing_raw:
            return {
                "duplicate": True,
                "duplicate_reason": "Raw Text match",
                "duplicate_match": task.get("Raw Text"),
            }

        if normalized_title and normalized_title == existing_title:
            return {
                "duplicate": True,
                "duplicate_reason": "Normalized Title match",
                "duplicate_match": task.get("Raw Text"),
            }

    return {
        "duplicate": False,
        "duplicate_reason": "",
        "duplicate_match": "",
    }


def is_duplicate(text, category, existing_tasks):
    parsed_task = {
        "raw_text": text,
        "normalized_title": text,
        "category": category,
    }

    result = find_duplicate_task(parsed_task, existing_tasks)
    return result["duplicate"]
