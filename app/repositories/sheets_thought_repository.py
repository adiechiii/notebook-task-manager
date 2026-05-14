from app.integrations.google_sheets_client import get_workbook
from app.schemas.thought_schema import THOUGHTS_HEADERS, THOUGHTS_WORKSHEET_NAME


SHEET_NAME = "NotebookTasksDB"


class SheetsThoughtRepository:
    def __init__(self):
        self.workbook = get_workbook(SHEET_NAME)

    def inspect_schema(self):
        worksheets = self.workbook.worksheets()
        worksheet = None

        for candidate in worksheets:
            if candidate.title == THOUGHTS_WORKSHEET_NAME:
                worksheet = candidate
                break

        if not worksheet:
            return {
                "exists": False,
                "headers_match": None,
                "existing_headers": [],
                "warnings": [
                    "Thoughts worksheet does not exist. Dry run only; no worksheet was created.",
                ],
            }

        existing_headers = worksheet.row_values(1)
        headers_match = existing_headers == THOUGHTS_HEADERS
        warnings = []

        if not headers_match:
            warnings.append(
                "Thoughts worksheet already exists with headers that do not match the approved schema. No changes will be made."
            )

        return {
            "exists": True,
            "headers_match": headers_match,
            "existing_headers": existing_headers,
            "warnings": warnings,
        }

    def create_schema_if_missing(self):
        inspection = self.inspect_schema()

        if inspection["exists"]:
            return {
                **inspection,
                "created_worksheet": False,
            }

        worksheet = self.workbook.add_worksheet(
            title=THOUGHTS_WORKSHEET_NAME,
            rows=1,
            cols=len(THOUGHTS_HEADERS),
        )

        try:
            worksheet.update("A1", [THOUGHTS_HEADERS])
        except Exception:
            return {
                "exists": True,
                "headers_match": False,
                "existing_headers": [],
                "warnings": [
                    "Worksheet may have been created, but header setup failed. Manual inspection required.",
                ],
                "created_worksheet": True,
            }

        return {
            "exists": True,
            "headers_match": True,
            "existing_headers": THOUGHTS_HEADERS,
            "warnings": [],
            "created_worksheet": True,
        }

    def _worksheet(self):
        return self.workbook.worksheet(THOUGHTS_WORKSHEET_NAME)

    def read_thoughts(self):
        return self._worksheet().get_all_records()

    def find_duplicate_candidates(self, raw_thought: str, project: str = ""):
        wanted_raw_thought = _normalized_key(raw_thought)
        wanted_project = _normalized_key(project)
        candidates = []

        if not wanted_raw_thought:
            return candidates

        for row in self.read_thoughts():
            row_raw_thought = _normalized_key(row.get("Raw Thought"))
            row_project = _normalized_key(row.get("Project"))

            if row_raw_thought != wanted_raw_thought:
                continue

            if row_project == wanted_project or not row_project or not wanted_project:
                candidates.append(_thought_from_row(row))

        return candidates


def _normalized_key(value):
    return " ".join(str(value or "").strip().lower().split())


def _thought_from_row(row):
    return {
        "thought_id": row.get("Thought ID"),
        "raw_thought": row.get("Raw Thought") or "",
        "summary": row.get("Summary") or "",
        "thought_type": row.get("Thought Type") or "",
        "mood": row.get("Mood") or "",
        "energy": row.get("Energy") or "",
        "project": row.get("Project") or "",
        "tags": row.get("Tags") or "",
        "status": row.get("Status") or "",
        "source_type": row.get("Source Type") or "",
        "created_at": row.get("Created At") or None,
        "updated_at": row.get("Updated At") or None,
    }
