from pydantic import BaseModel


THOUGHTS_WORKSHEET_NAME = "Thoughts"
CREATE_THOUGHTS_WORKSHEET_CONFIRMATION = "CREATE THOUGHTS WORKSHEET"
CREATE_THOUGHT_CONFIRMATION = "CREATE THOUGHT"
THOUGHTS_HEADERS = [
    "Thought ID",
    "Raw Thought",
    "Summary",
    "Thought Type",
    "Mood",
    "Energy",
    "Project",
    "Tags",
    "Status",
    "Source Type",
    "Created At",
    "Updated At",
]
SUGGESTED_THOUGHT_TYPES = [
    "Idea",
    "Reflection",
    "Concern",
    "Insight",
    "Question",
    "Journal",
]
THOUGHTS_SCHEMA_PREVIEW_WARNINGS = [
    "Preview only. No worksheet was created.",
    "Creating the Thoughts worksheet will require exact confirmation: CREATE THOUGHTS WORKSHEET.",
]


class ThoughtSchemaPreviewResponse(BaseModel):
    dry_run: bool
    preview_only: bool
    creates_worksheet: bool
    worksheet_name: str
    required_confirmation: str
    headers: list[str]
    suggested_thought_types: list[str]
    warnings: list[str]


class ThoughtSchemaSetupRequest(BaseModel):
    dry_run: bool = True
    confirmation: str = ""


class ThoughtSchemaSetupResponse(BaseModel):
    dry_run: bool
    worksheet_name: str
    exists: bool
    creates_worksheet: bool
    created_worksheet: bool
    headers_match: bool | None
    expected_headers: list[str]
    existing_headers: list[str]
    warnings: list[str]


class ThoughtCreatePreviewRequest(BaseModel):
    raw_thought: str
    summary: str = ""
    thought_type: str = ""
    mood: str = ""
    energy: str = ""
    project: str = ""
    tags: str = ""
    status: str = ""
    source_type: str = ""


class ThoughtPreviewItem(BaseModel):
    thought_id: str | None = None
    raw_thought: str
    summary: str
    thought_type: str
    mood: str
    energy: str
    project: str
    tags: str
    status: str
    source_type: str
    created_at: str | None = None
    updated_at: str | None = None


class ThoughtCreatePreviewResponse(BaseModel):
    dry_run: bool
    would_create_thought: bool
    schema_ok: bool
    duplicate_candidates: list[ThoughtPreviewItem]
    thought: ThoughtPreviewItem
    warnings: list[str]


class ThoughtCreateRequest(ThoughtCreatePreviewRequest):
    confirmation: str


class ThoughtCreateResponse(BaseModel):
    created: bool
    schema_ok: bool
    duplicate_candidates: list[ThoughtPreviewItem]
    thought: ThoughtPreviewItem
    warnings: list[str]
