import uuid
from datetime import datetime

from app.integrations.google_sheets_client import get_workbook


MEMORY_FIELD_TO_COLUMN = {
    "memory_summary": "Memory Summary",
    "memory_type": "Memory Type",
    "entity": "Entity",
    "project": "Project",
    "tags": "Tags",
    "importance": "Importance",
    "status": "Status",
}


class SheetsMemoryRepository:
    def __init__(self):
        self.sheet = get_workbook("NotebookTasksDB").worksheet("Memories")

    def _memory_from_row(self, row):
        return {
            "memory_id": row.get("Memory ID"),
            "text": row.get("Raw Text"),
            "summary": row.get("Memory Summary"),
            "type": row.get("Memory Type"),
            "entity": row.get("Entity"),
            "project": row.get("Project"),
            "tags": row.get("Tags"),
            "importance": row.get("Importance"),
            "status": row.get("Status"),
            "updated_at": row.get("Updated At"),
        }

    # =========================
    # CREATE
    # =========================
    def create_memory(
        self,
        text: str,
        memory_type: str = "General",
        entity: str = "",
        project: str = "",
        tags: str = "",
        importance: str = "Medium",
    ):
        memory_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        summary = text.strip()

        row = [
            memory_id,
            text,
            summary,
            memory_type,
            entity,
            project,
            tags,
            importance,
            "Active",
            "text",
            "manual",
            now,
            now,
        ]

        self.sheet.append_row(row)
        return memory_id

    # =========================
    # SEARCH
    # =========================
    def search_memories(self, query: str):
        rows = self.sheet.get_all_records()
        q = query.strip().lower()

        memories = []

        for row in rows:
            searchable = " ".join([
                str(row.get("Raw Text", "")),
                str(row.get("Memory Summary", "")),
                str(row.get("Memory Type", "")),
                str(row.get("Entity", "")),
                str(row.get("Project", "")),
                str(row.get("Tags", "")),
            ]).lower()

            if not q or q in searchable:
                memories.append(self._memory_from_row(row))

        return memories

    # =========================
    # UPDATE
    # =========================
    def update_memory(self, memory_id: str, fields: dict):
        memory_id = str(memory_id or "").strip()

        if not memory_id:
            return False, None, ["Memory ID is required."]

        updates = {
            key: value
            for key, value in (fields or {}).items()
            if key in MEMORY_FIELD_TO_COLUMN and value is not None
        }

        if not updates:
            return False, None, ["No update fields were provided."]

        rows = self.sheet.get_all_records()
        matches = []

        for i, row in enumerate(rows):
            row_memory_id = str(row.get("Memory ID") or "").strip()
            if row_memory_id == memory_id:
                matches.append((i + 2, row))

        if not matches:
            return False, None, [f"No exact memory match found for ID '{memory_id}'."]

        if len(matches) > 1:
            return False, None, [f"Multiple exact memory matches found for ID '{memory_id}'. Update blocked."]

        row_num, row = matches[0]
        headers = self.sheet.row_values(1)
        header_to_index = {header: index for index, header in enumerate(headers, start=1)}
        now = datetime.utcnow().isoformat()

        for field, value in updates.items():
            column_name = MEMORY_FIELD_TO_COLUMN[field]
            column_index = header_to_index.get(column_name)
            if not column_index:
                continue

            self.sheet.update_cell(row_num, column_index, str(value).strip())

        updated_at_column = header_to_index.get("Updated At")
        if updated_at_column:
            self.sheet.update_cell(row_num, updated_at_column, now)

        updated_row = self.sheet.row_values(row_num)
        updated_record = {
            headers[i]: updated_row[i] if i < len(updated_row) else ""
            for i in range(len(headers))
        }

        return True, self._memory_from_row(updated_record), []
