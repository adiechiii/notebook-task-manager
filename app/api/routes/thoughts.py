from fastapi import APIRouter

from app.schemas.thought_schema import (
    CREATE_THOUGHTS_WORKSHEET_CONFIRMATION,
    SUGGESTED_THOUGHT_TYPES,
    THOUGHTS_HEADERS,
    THOUGHTS_SCHEMA_PREVIEW_WARNINGS,
    THOUGHTS_WORKSHEET_NAME,
    ThoughtSchemaPreviewResponse,
)


router = APIRouter()


@router.get(
    "/thoughts/schema-preview",
    response_model=ThoughtSchemaPreviewResponse,
)
def preview_thoughts_schema():
    return ThoughtSchemaPreviewResponse(
        dry_run=True,
        preview_only=True,
        creates_worksheet=False,
        worksheet_name=THOUGHTS_WORKSHEET_NAME,
        required_confirmation=CREATE_THOUGHTS_WORKSHEET_CONFIRMATION,
        headers=THOUGHTS_HEADERS,
        suggested_thought_types=SUGGESTED_THOUGHT_TYPES,
        warnings=THOUGHTS_SCHEMA_PREVIEW_WARNINGS,
    )
