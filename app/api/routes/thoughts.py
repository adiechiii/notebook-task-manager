from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.schemas.thought_schema import (
    CREATE_THOUGHTS_WORKSHEET_CONFIRMATION,
    SUGGESTED_THOUGHT_TYPES,
    THOUGHTS_HEADERS,
    THOUGHTS_SCHEMA_PREVIEW_WARNINGS,
    THOUGHTS_WORKSHEET_NAME,
    ThoughtCreatePreviewRequest,
    ThoughtCreatePreviewResponse,
    ThoughtPreviewItem,
    ThoughtSchemaSetupRequest,
    ThoughtSchemaSetupResponse,
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


def _setup_response(
    *,
    dry_run: bool,
    inspection: dict,
    creates_worksheet: bool,
    created_worksheet: bool = False,
):
    return ThoughtSchemaSetupResponse(
        dry_run=dry_run,
        worksheet_name=THOUGHTS_WORKSHEET_NAME,
        exists=inspection["exists"],
        creates_worksheet=creates_worksheet,
        created_worksheet=created_worksheet,
        headers_match=inspection["headers_match"],
        expected_headers=THOUGHTS_HEADERS,
        existing_headers=inspection["existing_headers"],
        warnings=inspection["warnings"],
    )


@router.post(
    "/thoughts/schema-setup",
    response_model=ThoughtSchemaSetupResponse,
)
def setup_thoughts_schema(request: ThoughtSchemaSetupRequest):
    if not request.dry_run and request.confirmation != CREATE_THOUGHTS_WORKSHEET_CONFIRMATION:
        return JSONResponse(
            status_code=400,
            content=ThoughtSchemaSetupResponse(
                dry_run=False,
                worksheet_name=THOUGHTS_WORKSHEET_NAME,
                exists=False,
                creates_worksheet=False,
                created_worksheet=False,
                headers_match=None,
                expected_headers=THOUGHTS_HEADERS,
                existing_headers=[],
                warnings=[
                    "Exact confirmation phrase is required. No worksheet was created.",
                ],
            ).model_dump(),
        )

    from app.repositories.sheets_thought_repository import SheetsThoughtRepository

    repo = SheetsThoughtRepository()

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


def _clean(value: str) -> str:
    return str(value or "").strip()


def _preview_item(request: ThoughtCreatePreviewRequest) -> ThoughtPreviewItem:
    raw_thought = _clean(request.raw_thought)
    summary = _clean(request.summary) or raw_thought

    return ThoughtPreviewItem(
        thought_id=None,
        raw_thought=raw_thought,
        summary=summary,
        thought_type=_clean(request.thought_type) or "Reflection",
        mood=_clean(request.mood),
        energy=_clean(request.energy),
        project=_clean(request.project),
        tags=_clean(request.tags),
        status=_clean(request.status) or "Active",
        source_type=_clean(request.source_type) or "text",
        created_at=None,
        updated_at=None,
    )


@router.post(
    "/thoughts/create-preview",
    response_model=ThoughtCreatePreviewResponse,
)
def preview_thought_create(request: ThoughtCreatePreviewRequest):
    from app.repositories.sheets_thought_repository import SheetsThoughtRepository

    repo = SheetsThoughtRepository()
    inspection = repo.inspect_schema()
    preview_thought = _preview_item(request)

    if not inspection["exists"] or inspection["headers_match"] is not True:
        warnings = list(inspection["warnings"])
        warnings.append("Thoughts schema must exist with approved headers before thoughts can be created.")
        return ThoughtCreatePreviewResponse(
            dry_run=True,
            would_create_thought=False,
            schema_ok=False,
            duplicate_candidates=[],
            thought=preview_thought,
            warnings=warnings,
        )

    if not preview_thought.raw_thought:
        return ThoughtCreatePreviewResponse(
            dry_run=True,
            would_create_thought=False,
            schema_ok=True,
            duplicate_candidates=[],
            thought=preview_thought,
            warnings=[
                "Raw thought is required. Preview only; no thought was created.",
            ],
        )

    duplicate_candidates = repo.find_duplicate_candidates(
        preview_thought.raw_thought,
        preview_thought.project,
    )
    warnings = []

    if duplicate_candidates:
        warnings.append("Possible duplicate thought found. Preview only; no thought was created.")

    return ThoughtCreatePreviewResponse(
        dry_run=True,
        would_create_thought=True,
        schema_ok=True,
        duplicate_candidates=duplicate_candidates,
        thought=preview_thought,
        warnings=warnings,
    )
