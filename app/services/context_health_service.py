from app.integrations.google_sheets_client import get_workbook


WORKBOOK_NAME = "NotebookTasksDB"

SHEET_CHECKS = [
    {
        "name": "Tasks",
        "id_column": "Task ID",
        "expected_headers": [
            "Task ID", "Raw Text", "Normalized Title", "Category", "Status",
            "Page Date", "Capture Date", "Source Type", "Source Reference",
            "Duplicate Flag", "Review Required", "Created At", "Updated At",
            "Completion Date", "Priority", "Project",
        ],
        "required_fields": ["Task ID", "Raw Text", "Status", "Priority", "Project"],
    },
    {
        "name": "Projects",
        "id_column": "Project ID",
        "expected_headers": [
            "Project ID", "Project Name", "Description", "Goal", "Status",
            "Priority", "Category", "Tags", "Created At", "Updated At",
        ],
        "required_fields": ["Project ID", "Project Name", "Status", "Priority", "Category"],
    },
    {
        "name": "Memories",
        "id_column": "Memory ID",
        "expected_headers": [
            "Memory ID", "Raw Text", "Memory Summary", "Memory Type", "Entity",
            "Project", "Tags", "Importance", "Status", "Source Type",
            "Source Reference", "Created At", "Updated At",
        ],
        "required_fields": ["Memory ID", "Raw Text", "Memory Summary", "Status", "Importance"],
    },
    {
        "name": "Decisions",
        "id_column": "Decision ID",
        "expected_headers": [
            "Decision ID", "Decision", "Context", "Rationale", "Outcome",
            "Tradeoffs", "Project", "Tags", "Status", "Importance",
            "Source Type", "Capture Source", "Created At", "Updated At",
        ],
        "required_fields": ["Decision ID", "Decision", "Status", "Importance", "Project"],
    },
]


def build_context_health():
    workbook = get_workbook(WORKBOOK_NAME)
    checked_sheets = []
    warnings = []
    recommendations = []

    for config in SHEET_CHECKS:
        sheet_name = config["name"]
        sheet_warnings = []

        try:
            sheet = workbook.worksheet(sheet_name)
        except Exception:
            message = f"{sheet_name} sheet is missing."
            sheet_warnings.append(message)
            warnings.append(message)
            recommendations.append(f"Create or restore the {sheet_name} sheet with the approved headers.")
            checked_sheets.append({
                "name": sheet_name,
                "exists": False,
                "headers_match": None,
                "row_count": 0,
                "missing_id_count": 0,
                "duplicate_ids": [],
                "missing_required_fields": {},
                "warnings": sheet_warnings,
            })
            continue

        headers = sheet.row_values(1)
        rows = sheet.get_all_records()
        headers_match = headers == config["expected_headers"]

        if not headers_match:
            message = f"{sheet_name} headers do not match the approved schema."
            sheet_warnings.append(message)
            warnings.append(message)
            recommendations.append(f"Review the {sheet_name} sheet headers before writing new data.")

        id_column = config["id_column"]
        ids = [str(row.get(id_column) or "").strip() for row in rows]
        missing_id_count = sum(1 for value in ids if not value)
        duplicate_ids = sorted({value for value in ids if value and ids.count(value) > 1})

        if missing_id_count:
            message = f"{sheet_name} has {missing_id_count} row(s) missing {id_column}."
            sheet_warnings.append(message)
            warnings.append(message)
            recommendations.append(f"Fill missing {id_column} values in {sheet_name}.")

        if duplicate_ids:
            message = f"{sheet_name} has duplicate IDs."
            sheet_warnings.append(message)
            warnings.append(message)
            recommendations.append(f"Resolve duplicate IDs in {sheet_name} before bulk updates.")

        missing_required_fields = {}
        for field in config["required_fields"]:
            missing_count = sum(1 for row in rows if not str(row.get(field) or "").strip())
            missing_required_fields[field] = missing_count

            if missing_count:
                message = f"{sheet_name} has {missing_count} row(s) missing {field}."
                sheet_warnings.append(message)
                warnings.append(message)

        checked_sheets.append({
            "name": sheet_name,
            "exists": True,
            "headers_match": headers_match,
            "row_count": len(rows),
            "missing_id_count": missing_id_count,
            "duplicate_ids": duplicate_ids,
            "missing_required_fields": missing_required_fields,
            "warnings": sheet_warnings,
        })

    if not warnings:
        recommendations.append("Context health looks good. No immediate cleanup is required.")

    return {
        "ok": not warnings,
        "checked_sheets": checked_sheets,
        "warnings": warnings,
        "recommendations": recommendations,
    }
