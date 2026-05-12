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
    def create_task(self, text: str, normalized_title: str = None, page_date: str = "", priority: str = "Medium", category: str = "General", duplicate_flag: str = "FALSE", review_required: str = "FALSE", project: str = ""):
        task_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()

        title = normalized_title if normalized_title else text

        row = [
            task_id,
            text,
            title,
            category,
            "Pending",
            page_date,
            now,
            "text",
            "manual",
            duplicate_flag,
            review_required,
            now,
            now,
            "",
            priority,
            project
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
                "status": row.get("Status"),
                "project": row.get("Project"),
            })

        return tasks

    # =========================
    # ARCHIVE PREVIEW
    # =========================
    def get_archive_preview_candidates(self, status="Done", older_than_days=0, include_done=True):
        rows = self.sheet.get_all_records()
        now = datetime.utcnow()
        candidates = []
        wanted_status = str(status or "").strip().lower()
        include_done = bool(include_done)
        older_than_days = max(int(older_than_days or 0), 0)

        for row in rows:
            row_status = str(row.get("Status", "")).strip()
            row_status_lower = row_status.lower()

            if include_done:
                status_matches = row_status_lower in {wanted_status, "done"}
            else:
                status_matches = row_status_lower == wanted_status

            if not status_matches:
                continue

            date_source = str(row.get("Completion Date") or row.get("Updated At") or "").strip()
            age_days = None

            if date_source:
                try:
                    age_days = (now - datetime.fromisoformat(date_source)).days
                except ValueError:
                    age_days = None

            if age_days is not None and age_days < older_than_days:
                continue

            candidates.append({
                "task_id": row.get("Task ID"),
                "text": row.get("Raw Text"),
                "title": row.get("Normalized Title"),
                "status": row_status,
                "project": row.get("Project"),
                "updated_at": row.get("Updated At"),
                "completion_date": row.get("Completion Date"),
                "age_days": age_days,
            })

        return candidates

    def archive_tasks(self, status="Done", older_than_days=0, include_done=True):
        candidates = self.get_archive_preview_candidates(
            status=status,
            older_than_days=older_than_days,
            include_done=include_done,
        )
        candidate_ids = {candidate.get("task_id") for candidate in candidates}
        warnings = []

        if not candidate_ids:
            return [], warnings

        rows = self.sheet.get_all_records()
        row_updates = []
        seen_task_ids = set()
        allowed_statuses = {"done", "completed"}

        for i, row in enumerate(rows):
            task_id = row.get("Task ID")
            if task_id not in candidate_ids:
                continue

            row_status = str(row.get("Status", "")).strip()
            row_status_lower = row_status.lower()

            if not task_id:
                warnings.append("Archive blocked because a candidate is missing Task ID.")
                return [], warnings

            if task_id in seen_task_ids:
                warnings.append("Archive blocked because duplicate candidate Task IDs were found.")
                return [], warnings

            seen_task_ids.add(task_id)

            if row_status_lower not in allowed_statuses:
                warnings.append("Archive blocked because a candidate is no longer Done or Completed.")
                return [], warnings

            row_updates.append({
                "row_num": i + 2,
                "task": {
                    "task_id": task_id,
                    "text": row.get("Raw Text"),
                    "title": row.get("Normalized Title"),
                    "status": "Archived",
                    "previous_status": row_status,
                    "project": row.get("Project"),
                    "updated_at": None,
                    "completion_date": row.get("Completion Date"),
                },
            })

        if len(row_updates) != len(candidate_ids):
            warnings.append("Archive blocked because one or more candidates could not be re-validated.")
            return [], warnings

        now = datetime.utcnow().isoformat()
        archived = []

        for update in row_updates:
            row_num = update["row_num"]
            task = update["task"]

            self.sheet.update_cell(row_num, 5, "Archived")
            self.sheet.update_cell(row_num, 13, now)

            task["updated_at"] = now
            archived.append(task)

        return archived, warnings

    # =========================
    # COMMAND CENTER
    # =========================
    def get_command_center_tasks(self):
        rows = self.sheet.get_all_records()

        tasks = []

        for row in rows:
            if str(row.get("Status", "")).strip().lower() == "archived":
                continue

            tasks.append({
                "text": row.get("Raw Text"),
                "title": row.get("Normalized Title"),
                "status": row.get("Status"),
                "page_date": str(row.get("Page Date", "")).strip(),
                "category": row.get("Category"),
                "priority": row.get("Priority"),
                "project": row.get("Project"),
            })

        return tasks
