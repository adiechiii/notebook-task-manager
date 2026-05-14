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


class DecisionSchemaSetupRequest(BaseModel):
    dry_run: bool = True
    confirmation: str = ""


class DecisionSchemaSetupResponse(BaseModel):
    dry_run: bool
    worksheet_name: str
    exists: bool
    creates_worksheet: bool
    created_worksheet: bool
    headers_match: bool | None
    expected_headers: list[str]
    existing_headers: list[str]
    warnings: list[str]


class DecisionCreatePreviewRequest(BaseModel):
    decision: str
    context: str = ""
    rationale: str = ""
    outcome: str = ""
    tradeoffs: str = ""
    project: str = ""
    tags: str = ""
    status: str = ""
    importance: str = ""
    source_type: str = ""
    capture_source: str = ""


class DecisionPreviewItem(BaseModel):
    decision_id: str | None = None
    decision: str
    context: str = ""
    rationale: str = ""
    outcome: str = ""
    tradeoffs: str = ""
    project: str = ""
    tags: str = ""
    status: str
    importance: str
    source_type: str
    capture_source: str
    created_at: str | None = None
    updated_at: str | None = None


class DecisionCreatePreviewResponse(BaseModel):
    dry_run: bool
    would_create_decision: bool
    schema_ok: bool
    duplicate_candidates: list[DecisionPreviewItem]
    decision: DecisionPreviewItem
    warnings: list[str]
