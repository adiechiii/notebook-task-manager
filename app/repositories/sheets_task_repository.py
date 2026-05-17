import uuid
from datetime import datetime

from app.integrations.google_sheets_client import get_workbook


TASK_BULK_FIELD_TO_COLUMN = {
    "status": "Status",
    "priority": "Priority",
    "category": "Category",
    "project": "Project",
    "page_date": "Page Date",
}


class SheetsTaskRepository:
    def __init__(self):
        self.sheet = get_workbook("NotebookTasksDB").worksheet("Tasks")

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
                    "row": i + 2,
                    "status": row.get("Status")
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

    def archive_duplicate_task_ids(self, task_ids):
        requested_ids = {str(task_id or "").strip() for task_id in task_ids}
        requested_ids.discard("")
        warnings = []

        if not requested_ids:
            return [], warnings

        rows = self.sheet.get_all_records()
        row_updates = []
        seen_task_ids = set()

        for i, row in enumerate(rows):
            task_id = str(row.get("Task ID") or "").strip()
            if task_id not in requested_ids:
                continue

            if task_id in seen_task_ids:
                warnings.append("Duplicate cleanup archive blocked because duplicate Task IDs were found.")
                return [], warnings

            seen_task_ids.add(task_id)

            row_status = str(row.get("Status", "")).strip()
            if row_status.lower() == "archived":
                warnings.append("Duplicate cleanup archive blocked because a candidate is already Archived.")
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
                },
            })

        if len(row_updates) != len(requested_ids):
            warnings.append("Duplicate cleanup archive blocked because one or more Task IDs could not be re-validated.")
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

    def get_active_tasks_for_duplicate_cleanup(self):
        rows = self.sheet.get_all_records()

        tasks = []

        for row in rows:
            if str(row.get("Status", "")).strip().lower() == "archived":
                continue

            tasks.append({
                "task_id": row.get("Task ID"),
                "text": row.get("Raw Text"),
                "title": row.get("Normalized Title"),
                "status": row.get("Status"),
                "page_date": str(row.get("Page Date", "")).strip(),
                "category": row.get("Category"),
                "priority": row.get("Priority"),
                "project": row.get("Project"),
                "created_at": row.get("Created At"),
                "updated_at": row.get("Updated At"),
                "duplicate_flag": row.get("Duplicate Flag"),
                "review_required": row.get("Review Required"),
            })

        return tasks

    def _task_from_row(self, row):
        return {
            "task_id": row.get("Task ID"),
            "text": row.get("Raw Text"),
            "title": row.get("Normalized Title"),
            "status": row.get("Status"),
            "page_date": str(row.get("Page Date", "")).strip(),
            "category": row.get("Category"),
            "priority": row.get("Priority"),
            "project": row.get("Project"),
            "updated_at": row.get("Updated At"),
            "completion_date": row.get("Completion Date"),
        }

    def bulk_update_tasks(self, updates: list[dict]):
        warnings = []
        cleaned_updates = []
        seen_task_ids = set()

        for item in updates or []:
            task_id = str(item.get("task_id") or "").strip()

            if not task_id:
                warnings.append("Skipped an update because task_id is required.")
                continue

            if task_id in seen_task_ids:
                warnings.append(f"Duplicate task_id '{task_id}' in request. Bulk update blocked.")
                return [], warnings

            seen_task_ids.add(task_id)

            fields = {
                key: value
                for key, value in item.items()
                if key in TASK_BULK_FIELD_TO_COLUMN and value is not None
            }

            if not fields:
                warnings.append(f"Skipped task_id '{task_id}' because no update fields were provided.")
                continue

            cleaned_updates.append({
                "task_id": task_id,
                "fields": fields,
            })

        if not cleaned_updates:
            return [], warnings or ["No valid task updates were provided."]

        rows = self.sheet.get_all_records()
        headers = self.sheet.row_values(1)
        header_to_index = {header: index for index, header in enumerate(headers, start=1)}

        row_matches = {}
        duplicate_sheet_ids = set()

        for i, row in enumerate(rows):
            task_id = str(row.get("Task ID") or "").strip()
            if not task_id:
                continue

            if task_id in row_matches:
                duplicate_sheet_ids.add(task_id)
                continue

            row_matches[task_id] = (i + 2, row)

        if duplicate_sheet_ids:
            warnings.append("Bulk update blocked because duplicate Task IDs were found in the sheet.")
            return [], warnings

        now = datetime.utcnow().isoformat()
        updated_tasks = []

        for update in cleaned_updates:
            task_id = update["task_id"]
            match = row_matches.get(task_id)

            if not match:
                warnings.append(f"No exact task match found for ID '{task_id}'. Skipped.")
                continue

            row_num, row = match
            fields = update["fields"]

            for field, value in fields.items():
                column_name = TASK_BULK_FIELD_TO_COLUMN[field]
                column_index = header_to_index.get(column_name)
                if not column_index:
                    warnings.append(f"Column '{column_name}' was not found. Field '{field}' was skipped for task_id '{task_id}'.")
                    continue

                self.sheet.update_cell(row_num, column_index, str(value).strip())

            updated_at_column = header_to_index.get("Updated At")
            if updated_at_column:
                self.sheet.update_cell(row_num, updated_at_column, now)

            if str(fields.get("status", "")).strip().lower() == "done":
                completion_date_column = header_to_index.get("Completion Date")
                if completion_date_column:
                    self.sheet.update_cell(row_num, completion_date_column, now)

            updated_row = self.sheet.row_values(row_num)
            updated_record = {
                headers[i]: updated_row[i] if i < len(updated_row) else ""
                for i in range(len(headers))
            }
            updated_tasks.append(self._task_from_row(updated_record))

        return updated_tasks, warnings
