from pydantic import BaseModel


DECISIONS_WORKSHEET_NAME = "Decisions"
CREATE_DECISIONS_WORKSHEET_CONFIRMATION = "CREATE DECISIONS WORKSHEET"
DECISIONS_HEADERS = [
    "Decision ID",
    "Decision",
    "Context",
    "Rationale",
    "Outcome",
    "Tradeoffs",
    "Project",
    "Tags",
    "Status",
    "Importance",
    "Source Type",
    "Capture Source",
    "Created At",
    "Updated At",
]
DECISIONS_SCHEMA_PREVIEW_WARNINGS = [
    "Preview only. No worksheet was created.",
    "Creating the Decisions worksheet will require exact confirmation.",
]


class DecisionSchemaPreviewResponse(BaseModel):
    dry_run: bool
    schema_changes: bool
    creates_worksheet: bool
    worksheet_name: str
    required_confirmation: str
    headers: list[str]
    warnings: list[str]
