from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.decision_schema import (
    CREATE_DECISIONS_WORKSHEET_CONFIRMATION,
    DECISIONS_HEADERS,
    DECISIONS_SCHEMA_PREVIEW_WARNINGS,
    DECISIONS_WORKSHEET_NAME,
    DecisionSchemaSetupRequest,
    DecisionSchemaSetupResponse,
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


def _setup_response(
    *,
    dry_run: bool,
    inspection: dict,
    creates_worksheet: bool,
    created_worksheet: bool = False,
):
    return DecisionSchemaSetupResponse(
        dry_run=dry_run,
        worksheet_name=DECISIONS_WORKSHEET_NAME,
        exists=inspection["exists"],
        creates_worksheet=creates_worksheet,
        created_worksheet=created_worksheet,
        headers_match=inspection["headers_match"],
        expected_headers=DECISIONS_HEADERS,
        existing_headers=inspection["existing_headers"],
        warnings=inspection["warnings"],
    )


@router.post(
    "/decisions/schema-setup",
    response_model=DecisionSchemaSetupResponse,
)
def setup_decisions_schema(request: DecisionSchemaSetupRequest):
    if not request.dry_run and request.confirmation != CREATE_DECISIONS_WORKSHEET_CONFIRMATION:
        return JSONResponse(
            status_code=400,
            content=DecisionSchemaSetupResponse(
                dry_run=False,
                worksheet_name=DECISIONS_WORKSHEET_NAME,
                exists=False,
                creates_worksheet=False,
                created_worksheet=False,
                headers_match=None,
                expected_headers=DECISIONS_HEADERS,
                existing_headers=[],
                warnings=[
                    "Exact confirmation phrase is required. No worksheet was created.",
                ],
            ).model_dump(),
        )

    from app.repositories.sheets_decision_repository import SheetsDecisionRepository

    repo = SheetsDecisionRepository()

    if request.dry_run:
        inspection = repo.inspect_schema()
        return _setup_response(
            dry_run=True,
            inspection=inspection,
            creates_worksheet=False,
        )

    result = repo.create_schema_if_missing()
    creates_worksheet = result["created_worksheet"]
    return _setup_response(
        dry_run=False,
        inspection=result,
        creates_worksheet=creates_worksheet,
        created_worksheet=result["created_worksheet"],
    )
