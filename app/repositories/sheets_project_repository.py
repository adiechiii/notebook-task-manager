import uuid
from datetime import datetime

from app.integrations.google_sheets_client import get_workbook


PROJECT_FIELD_TO_COLUMN = {
    "description": "Description",
    "goal": "Goal",
    "status": "Status",
    "priority": "Priority",
    "category": "Category",
    "tags": "Tags",
}


class SheetsProjectRepository:
    def __init__(self):
        self.sheet = get_workbook("NotebookTasksDB").worksheet("Projects")

    def _project_from_row(self, row):
        return {
            "name": row.get("Project Name"),
            "priority": row.get("Priority"),
            "category": row.get("Category"),
            "description": row.get("Description"),
            "goal": row.get("Goal"),
            "tags": row.get("Tags"),
            "status": row.get("Status"),
            "updated_at": row.get("Updated At"),
        }

    # =========================
    # CREATE
    # =========================
    def create_project(self, name: str, description: str = ""):
        project_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        row = [
            project_id,
            name.strip(),
            description.strip(),
            "",
            "Active",
            "Medium",
            "General",
            "",
            now,
            now,
        ]

        self.sheet.append_row(row)
        return project_id

    # =========================
    # SEARCH
    # =========================
    def search_projects(self, query: str):
        rows = self.sheet.get_all_records()
        q = query.strip().lower()

        projects = []

        for row in rows:
            searchable = " ".join([
                str(row.get("Project Name", "")),
                str(row.get("Description", "")),
                str(row.get("Goal", "")),
                str(row.get("Status", "")),
                str(row.get("Priority", "")),
                str(row.get("Category", "")),
                str(row.get("Tags", "")),
            ]).lower()

            if not q or q in searchable:
                projects.append(self._project_from_row(row))

        return projects

    # =========================
    # UPDATE
    # =========================
    def update_project(self, name: str, fields: dict):
        warnings = []
        project_name = str(name or "").strip()

        if not project_name:
            return False, None, ["Project name is required."]

        updates = {
            key: value
            for key, value in (fields or {}).items()
            if key in PROJECT_FIELD_TO_COLUMN and value is not None
        }

        if not updates:
            return False, None, ["No update fields were provided."]

        rows = self.sheet.get_all_records()
        matches = []

        for i, row in enumerate(rows):
            row_name = str(row.get("Project Name") or "").strip()
            if row_name.casefold() == project_name.casefold():
                matches.append((i + 2, row))

        if not matches:
            return False, None, [f"No exact project match found for '{project_name}'."]

        if len(matches) > 1:
            return False, None, [f"Multiple exact project matches found for '{project_name}'. Update blocked."]

        row_num, row = matches[0]
        headers = self.sheet.row_values(1)
        header_to_index = {header: index for index, header in enumerate(headers, start=1)}
        now = datetime.utcnow().isoformat()

        for field, value in updates.items():
            column_name = PROJECT_FIELD_TO_COLUMN[field]
            column_index = header_to_index.get(column_name)
            if not column_index:
                warnings.append(f"Column '{column_name}' was not found. Field '{field}' was skipped.")
                continue

            self.sheet.update_cell(row_num, column_index, str(value).strip())

        updated_at_column = header_to_index.get("Updated At")
        if updated_at_column:
            self.sheet.update_cell(row_num, updated_at_column, now)
        else:
            warnings.append("Column 'Updated At' was not found.")

        updated_row = self.sheet.row_values(row_num)
        updated_record = {
            headers[i]: updated_row[i] if i < len(updated_row) else ""
            for i in range(len(headers))
        }

        return True, self._project_from_row(updated_record), warnings
