from app.integrations.google_sheets_client import get_workbook
from app.schemas.decision_schema import DECISIONS_HEADERS, DECISIONS_WORKSHEET_NAME


SHEET_NAME = "NotebookTasksDB"


DECISION_FIELD_TO_COLUMN = {
    "decision": "Decision",
    "context": "Context",
    "rationale": "Rationale",
    "outcome": "Outcome",
    "tradeoffs": "Tradeoffs",
    "project": "Project",
    "tags": "Tags",
    "status": "Status",
    "importance": "Importance",
}


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

    def create_decision(self, decision: dict):
        inspection = self.inspect_schema()

        if not inspection["exists"] or inspection["headers_match"] is not True:
            return {
                "created": False,
                "schema_ok": False,
                "decision": decision,
                "warnings": inspection["warnings"],
            }

        row = [
            decision["decision_id"],
            decision["decision"],
            decision["context"],
            decision["rationale"],
            decision["outcome"],
            decision["tradeoffs"],
            decision["project"],
            decision["tags"],
            decision["status"],
            decision["importance"],
            decision["source_type"],
            decision["capture_source"],
            decision["created_at"],
            decision["updated_at"],
        ]
        self._worksheet().append_row(row)

        return {
            "created": True,
            "schema_ok": True,
            "decision": decision,
            "warnings": [],
        }


    def update_decision(self, decision_id: str, fields: dict):
        inspection = self.inspect_schema()

        if not inspection["exists"] or inspection["headers_match"] is not True:
            return False, None, inspection["warnings"]

        decision_id = str(decision_id or "").strip()

        if not decision_id:
            return False, None, ["Decision ID is required."]

        updates = {
            key: value
            for key, value in (fields or {}).items()
            if key in DECISION_FIELD_TO_COLUMN and value is not None
        }

        if not updates:
            return False, None, ["No update fields were provided."]

        worksheet = self._worksheet()
        rows = worksheet.get_all_records()
        matches = []

        for i, row in enumerate(rows):
            row_decision_id = str(row.get("Decision ID") or "").strip()
            if row_decision_id == decision_id:
                matches.append((i + 2, row))

        if not matches:
            return False, None, [f"No exact decision match found for ID '{decision_id}'."]

        if len(matches) > 1:
            return False, None, [f"Multiple exact decision matches found for ID '{decision_id}'. Update blocked."]

        row_num, row = matches[0]
        headers = worksheet.row_values(1)
        header_to_index = {header: index for index, header in enumerate(headers, start=1)}
        now = __import__("datetime").datetime.utcnow().isoformat()

        for field, value in updates.items():
            column_name = DECISION_FIELD_TO_COLUMN[field]
            column_index = header_to_index.get(column_name)
            if not column_index:
                continue

            worksheet.update_cell(row_num, column_index, str(value).strip())

        updated_at_column = header_to_index.get("Updated At")
        if updated_at_column:
            worksheet.update_cell(row_num, updated_at_column, now)

        updated_row = worksheet.row_values(row_num)
        updated_record = {
            headers[i]: updated_row[i] if i < len(updated_row) else ""
            for i in range(len(headers))
        }

        return True, _decision_from_row(updated_record), []

    def search_decisions(
        self,
        query: str = "",
        status: str = "",
        project: str = "",
        importance: str = "",
        limit: int = 50,
    ):
        inspection = self.inspect_schema()

        if not inspection["exists"] or inspection["headers_match"] is not True:
            return {
                "schema_ok": False,
                "decisions": [],
                "warnings": inspection["warnings"],
            }

        normalized_query = _normalized_key(query)
        normalized_status = _normalized_key(status)
        normalized_project = _normalized_key(project)
        normalized_importance = _normalized_key(importance)
        safe_limit = _clamp_limit(limit)
        decisions = []

        for row in self.read_decisions():
            decision = _decision_from_row(row)

            if normalized_status and _normalized_key(decision["status"]) != normalized_status:
                continue

            if normalized_project and _normalized_key(decision["project"]) != normalized_project:
                continue

            if normalized_importance and _normalized_key(decision["importance"]) != normalized_importance:
                continue

            if normalized_query and normalized_query not in _searchable_decision_text(decision):
                continue

            decisions.append(decision)

        decisions.sort(
            key=lambda decision: decision.get("created_at") or decision.get("updated_at") or "",
            reverse=True,
        )

        return {
            "schema_ok": True,
            "decisions": decisions[:safe_limit],
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


def _searchable_decision_text(decision):
    return _normalized_key(
        " ".join(
            [
                decision.get("decision", ""),
                decision.get("context", ""),
                decision.get("rationale", ""),
                decision.get("outcome", ""),
                decision.get("tradeoffs", ""),
                decision.get("project", ""),
                decision.get("tags", ""),
                decision.get("status", ""),
                decision.get("importance", ""),
            ]
        )
    )


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
