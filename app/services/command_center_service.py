from datetime import datetime


def build_command_center(tasks):
    today = datetime.utcnow().date()

    command_center = {
        "today": [],
        "overdue": [],
        "upcoming": [],
        "no_date": [],
        "done": [],
    }

    for task in tasks:
        status = str(task.get("status", "")).strip()
        page_date = str(task.get("page_date", "")).strip()

        if status.lower() == "done":
            command_center["done"].append(task)
            continue

        if not page_date:
            command_center["no_date"].append(task)
            continue

        try:
            task_date = datetime.fromisoformat(page_date).date()
        except ValueError:
            command_center["no_date"].append(task)
            continue

        if task_date == today:
            command_center["today"].append(task)
        elif task_date < today:
            command_center["overdue"].append(task)
        else:
            command_center["upcoming"].append(task)

    return command_center
