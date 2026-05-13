from fastapi import APIRouter

from app.schemas.decision_schema import (
    CREATE_DECISIONS_WORKSHEET_CONFIRMATION,
    DECISIONS_HEADERS,
    DECISIONS_SCHEMA_PREVIEW_WARNINGS,
    DECISIONS_WORKSHEET_NAME,
    DecisionSchemaPreviewResponse,
)


router = APIRouter()


@router.get(
    "/decisions/schema-preview",
    response_model=DecisionSchemaPreviewResponse,
)
def preview_decisions_schema():
    return DecisionSchemaPreviewResponse(
        dry_run=True,
        schema_changes=True,
        creates_worksheet=False,
        worksheet_name=DECISIONS_WORKSHEET_NAME,
        required_confirmation=CREATE_DECISIONS_WORKSHEET_CONFIRMATION,
        headers=DECISIONS_HEADERS,
        warnings=DECISIONS_SCHEMA_PREVIEW_WARNINGS,
    )
