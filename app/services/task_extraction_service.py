def extract_tasks(text: str):
    lines = text.split("\n")
    tasks = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        category = "Business" if "report" in line.lower() else "Personal"

        tasks.append({
            "raw_text": line,
            "category": category,
            "page_date": ""
        })

    return tasks