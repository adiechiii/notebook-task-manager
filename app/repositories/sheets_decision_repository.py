from app.integrations.google_sheets_client import get_workbook
from app.schemas.decision_schema import DECISIONS_HEADERS, DECISIONS_WORKSHEET_NAME


SHEET_NAME = "NotebookTasksDB"


class SheetsDecisionRepository:
    def __init__(self):
        self.workbook = get_workbook(SHEET_NAME)

    def inspect_schema(self):
        worksheets = self.workbook.worksheets()
        worksheet = None

        for candidate in worksheets:
            if candidate.title == DECISIONS_WORKSHEET_NAME:
                worksheet = candidate
                break

        if not worksheet:
            return {
                "exists": False,
                "headers_match": None,
                "existing_headers": [],
                "warnings": [
                    "Decisions worksheet does not exist. Dry run only; no worksheet was created.",
                ],
            }

        existing_headers = worksheet.row_values(1)
        headers_match = existing_headers == DECISIONS_HEADERS
        warnings = []

        if not headers_match:
            warnings.append(
                "Decisions worksheet already exists with headers that do not match the approved schema. No changes will be made."
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
            title=DECISIONS_WORKSHEET_NAME,
            rows=1,
            cols=len(DECISIONS_HEADERS),
        )

        try:
            worksheet.update("A1", [DECISIONS_HEADERS])
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
            "existing_headers": DECISIONS_HEADERS,
            "warnings": [],
            "created_worksheet": True,
        }

    def _worksheet(self):
        return self.workbook.worksheet(DECISIONS_WORKSHEET_NAME)

    def read_decisions(self):
        return self._worksheet().get_all_records()

    def find_duplicate_candidates(self, decision: str, project: str = ""):
        wanted_decision = _normalized_key(decision)
        wanted_project = _normalized_key(project)
        candidates = []

        if not wanted_decision:
            return candidates

        for row in self.read_decisions():
            row_decision = _normalized_key(row.get("Decision"))
            row_project = _normalized_key(row.get("Project"))

            if row_decision != wanted_decision:
                continue

            if row_project == wanted_project or not row_project or not wanted_project:
                candidates.append(_decision_from_row(row))

        return candidates


def _normalized_key(value):
    return " ".join(str(value or "").strip().lower().split())


def _decision_from_row(row):
    return {
        "decision_id": row.get("Decision ID"),
        "decision": row.get("Decision") or "",
        "context": row.get("Context") or "",
        "rationale": row.get("Rationale") or "",
        "outcome": row.get("Outcome") or "",
        "tradeoffs": row.get("Tradeoffs") or "",
        "project": row.get("Project") or "",
        "tags": row.get("Tags") or "",
        "status": row.get("Status") or "",
        "importance": row.get("Importance") or "",
        "source_type": row.get("Source Type") or "",
        "capture_source": row.get("Capture Source") or "",
        "created_at": row.get("Created At") or None,
        "updated_at": row.get("Updated At") or None,
    }
