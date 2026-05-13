from datetime import datetime
import uuid

from app.integrations.google_sheets_client import get_workbook

SHEET_NAME = "NotebookTasksDB"
WORKSHEET_NAME = "StatusLog"


class SheetsStatusLogRepository:

    def __init__(self):
        self.sheet = get_workbook(SHEET_NAME).worksheet(WORKSHEET_NAME)

    def create_log(self, task_id, old_status, new_status, change_source="api"):
        now = datetime.utcnow().isoformat()

        row = [
            str(uuid.uuid4()),
            task_id,
            old_status,
            new_status,
            now,
            change_source
        ]

        self.sheet.append_row(row)

    def log_status_change(self, task_id, old_status, new_status):
        self.create_log(task_id, old_status, new_status)

    def get_logs_for_date(self, target_date, new_statuses=None):
        wanted_statuses = None
        if new_statuses:
            wanted_statuses = {
                str(status or "").strip().casefold()
                for status in new_statuses
            }

        logs = []
        skipped_invalid_dates = 0

        for row in self.sheet.get_all_records():
            changed_at = str(row.get("Changed At") or "").strip()
            if not changed_at:
                skipped_invalid_dates += 1
                continue

            try:
                changed_date = datetime.fromisoformat(
                    changed_at.replace("Z", "+00:00")
                ).date()
            except ValueError:
                skipped_invalid_dates += 1
                continue

            if changed_date != target_date:
                continue

            new_status = str(row.get("New Status") or "").strip()
            if wanted_statuses and new_status.casefold() not in wanted_statuses:
                continue

            logs.append({
                "log_id": row.get("Log ID"),
                "task_id": row.get("Task ID"),
                "old_status": str(row.get("Old Status") or "").strip(),
                "new_status": new_status,
                "changed_at": changed_at,
                "change_source": str(row.get("Change Source") or "").strip(),
            })

        return {
            "logs": logs,
            "skipped_invalid_dates": skipped_invalid_dates,
        }
