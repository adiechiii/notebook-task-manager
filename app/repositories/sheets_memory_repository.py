import uuid
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials


class SheetsMemoryRepository:
    def __init__(self):
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=scope,
        )

        client = gspread.authorize(creds)
        self.sheet = client.open("NotebookTasksDB").worksheet("Memories")

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
                memories.append({
                    "text": row.get("Raw Text"),
                    "summary": row.get("Memory Summary"),
                    "type": row.get("Memory Type"),
                    "entity": row.get("Entity"),
                    "project": row.get("Project"),
                    "tags": row.get("Tags"),
                    "importance": row.get("Importance"),
                    "status": row.get("Status"),
                })

        return memories
