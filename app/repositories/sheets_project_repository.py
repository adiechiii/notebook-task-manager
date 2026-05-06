import uuid
from datetime import datetime

import gspread
from google.oauth2.service_account import Credentials


class SheetsProjectRepository:
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
        self.sheet = client.open("NotebookTasksDB").worksheet("Projects")

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
                projects.append({
                    "name": row.get("Project Name"),
                    "description": row.get("Description"),
                    "goal": row.get("Goal"),
                    "status": row.get("Status"),
                    "priority": row.get("Priority"),
                    "category": row.get("Category"),
                    "tags": row.get("Tags"),
                })

        return projects
