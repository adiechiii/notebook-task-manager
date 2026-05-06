from app.services.date_parser_service import parse_date_from_text, normalize_task_title
from app.services.priority_service import parse_priority_from_text
from app.services.category_service import classify_category


def parse_tasks_from_text(text: str):
    parsed_tasks = []

    for line in text.split("\n"):
        task = line.strip()
        if not task:
            continue

        parsed_tasks.append({
            "raw_text": task,
            "normalized_title": normalize_task_title(task),
            "page_date": parse_date_from_text(task),
            "category": classify_category(task),
            "priority": parse_priority_from_text(task),
        })

    return parsed_tasks
