import uuid
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials


class SheetsTaskRepository:
    def __init__(self):
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_file(
            "credentials.json",
            scopes=scope
        )

        client = gspread.authorize(creds)

        self.sheet = client.open("NotebookTasksDB").worksheet("Tasks")

    # =========================
    # CREATE
    # =========================
    def create_task(self, text: str):
        task_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        row = [
            task_id,
            text,
            text,
            "General",
            "Pending",
            "",
            now,
            "text",
            "manual",
            "FALSE",
            "FALSE",
            now,
            now,
            ""
        ]

        self.sheet.append_row(row)
        return task_id

    # =========================
    # FIND BY TEXT
    # =========================
    def find_task_by_text(self, text: str):
        rows = self.sheet.get_all_records()
        search = text.strip().lower()

        for i, row in enumerate(rows):
            raw = str(row.get("Raw Text", "")).strip().lower()

            if raw == search or search in raw or raw in search:
                return {
                    "task_id": row.get("Task ID"),
                    "row": i + 2
                }

        return None

    # =========================
    # UPDATE
    # =========================
    def update_task_status(self, task_id: str, status: str):
        rows = self.sheet.get_all_records()

        for i, row in enumerate(rows):
            if row.get("Task ID") == task_id:
                row_num = i + 2
                now = datetime.utcnow().isoformat()

                self.sheet.update_cell(row_num, 5, status)
                self.sheet.update_cell(row_num, 13, now)

                if status.lower() == "done":
                    self.sheet.update_cell(row_num, 14, now)

                return True

        return False

    # =========================
    # DELETE
    # =========================
    def delete_task(self, task_id: str):
        rows = self.sheet.get_all_records()

        for i, row in enumerate(rows):
            if row.get("Task ID") == task_id:
                self.sheet.delete_rows(i + 2)
                return True

        return False

    # =========================
    # LIST
    # =========================
    def get_all_tasks(self, status=None):
        rows = self.sheet.get_all_records()

        tasks = []

        for row in rows:
            if status and row.get("Status") != status:
                continue

            tasks.append({
                "text": row.get("Raw Text"),
                "status": row.get("Status")
            })

        return tasks