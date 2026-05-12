from app.integrations.google_sheets_client import get_workbook
from datetime import datetime
import uuid

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
