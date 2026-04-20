def is_duplicate(text, category, existing_tasks):
    for task in existing_tasks:
        if task["Raw Text"].strip().lower() == text.strip().lower():
            return True
    return False