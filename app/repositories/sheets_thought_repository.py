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

    def create_thought(self, thought: dict):
        inspection = self.inspect_schema()

        if not inspection["exists"] or inspection["headers_match"] is not True:
            return {
                "created": False,
                "schema_ok": False,
                "thought": thought,
                "warnings": inspection["warnings"],
            }

        row = [
            thought["thought_id"],
            thought["raw_thought"],
            thought["summary"],
            thought["thought_type"],
            thought["mood"],
            thought["energy"],
            thought["project"],
            thought["tags"],
            thought["status"],
            thought["source_type"],
            thought["created_at"],
            thought["updated_at"],
        ]
        self._worksheet().append_row(row)

        return {
            "created": True,
            "schema_ok": True,
            "thought": thought,
            "warnings": [],
        }

    def search_thoughts(
        self,
        query: str = "",
        status: str = "",
        project: str = "",
        thought_type: str = "",
        limit: int = 50,
    ):
        inspection = self.inspect_schema()

        if not inspection["exists"] or inspection["headers_match"] is not True:
            return {
                "schema_ok": False,
                "thoughts": [],
                "warnings": inspection["warnings"],
            }

        normalized_query = _normalized_key(query)
        normalized_status = _normalized_key(status)
        normalized_project = _normalized_key(project)
        normalized_thought_type = _normalized_key(thought_type)
        safe_limit = _clamp_limit(limit)
        thoughts = []

        for row in self.read_thoughts():
            thought = _thought_from_row(row)

            if normalized_status and _normalized_key(thought["status"]) != normalized_status:
                continue

            if normalized_project and _normalized_key(thought["project"]) != normalized_project:
                continue

            if normalized_thought_type and _normalized_key(thought["thought_type"]) != normalized_thought_type:
                continue

            if normalized_query and normalized_query not in _searchable_thought_text(thought):
                continue

            thoughts.append(thought)

        thoughts.sort(
            key=lambda thought: thought.get("created_at") or thought.get("updated_at") or "",
            reverse=True,
        )

        return {
            "schema_ok": True,
            "thoughts": thoughts[:safe_limit],
            "warnings": [],
        }


def _normalized_key(value):
    return " ".join(str(value or "").strip().lower().split())


def _clamp_limit(value):
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = 50

    return min(max(limit, 1), 100)


def _searchable_thought_text(thought):
    return _normalized_key(
        " ".join(
            [
                thought.get("raw_thought", ""),
                thought.get("summary", ""),
                thought.get("thought_type", ""),
                thought.get("mood", ""),
                thought.get("energy", ""),
                thought.get("project", ""),
                thought.get("tags", ""),
                thought.get("status", ""),
            ]
        )
    )


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
