from app.integrations.google_sheets_client import get_client
from datetime import datetime
import uuid

SHEET_NAME = "NotebookTasksDB"
WORKSHEET_NAME = "StatusLog"


class SheetsStatusLogRepository:

    def __init__(self):
        client = get_client()
        self.sheet = client.open(SHEET_NAME).worksheet(WORKSHEET_NAME)

    def log_status_change(self, task_id, old_status, new_status):
        now = datetime.utcnow().isoformat()

        row = [
            str(uuid.uuid4()),
            task_id,
            old_status,
            new_status,
            now,
            "api"
        ]

        self.sheet.append_row(row)