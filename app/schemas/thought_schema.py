from pydantic import BaseModel


THOUGHTS_WORKSHEET_NAME = "Thoughts"
CREATE_THOUGHTS_WORKSHEET_CONFIRMATION = "CREATE THOUGHTS WORKSHEET"
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
