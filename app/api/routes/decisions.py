import uuid
from datetime import datetime

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from app.schemas.decision_schema import (
    CREATE_DECISION_CONFIRMATION,
    CREATE_DECISIONS_WORKSHEET_CONFIRMATION,
    DECISIONS_HEADERS,
    DECISIONS_SCHEMA_PREVIEW_WARNINGS,
    DECISIONS_WORKSHEET_NAME,
    DecisionCreateRequest,
    DecisionCreateResponse,
    DecisionCreatePreviewRequest,
    DecisionCreatePreviewResponse,
    DecisionPreviewItem,
    DecisionSearchResponse,
    DecisionUpdateRequest,
    DecisionUpdateResponse,
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


def _clean(value: str) -> str:
    return str(value or "").strip()


def _preview_item(request: DecisionCreatePreviewRequest) -> DecisionPreviewItem:
    return DecisionPreviewItem(
        decision_id=None,
        decision=_clean(request.decision),
        context=_clean(request.context),
        rationale=_clean(request.rationale),
        outcome=_clean(request.outcome),
        tradeoffs=_clean(request.tradeoffs),
        project=_clean(request.project),
        tags=_clean(request.tags),
        status=_clean(request.status) or "Active",
        importance=_clean(request.importance) or "Medium",
        source_type=_clean(request.source_type) or "text",
        capture_source=_clean(request.capture_source) or "manual",
        created_at=None,
        updated_at=None,
    )


def _created_item(request: DecisionCreateRequest) -> DecisionPreviewItem:
    now = datetime.utcnow().isoformat()
    return DecisionPreviewItem(
        decision_id=str(uuid.uuid4()),
        decision=_clean(request.decision),
        context=_clean(request.context),
        rationale=_clean(request.rationale),
        outcome=_clean(request.outcome),
        tradeoffs=_clean(request.tradeoffs),
        project=_clean(request.project),
        tags=_clean(request.tags),
        status=_clean(request.status) or "Active",
        importance=_clean(request.importance) or "Medium",
        source_type=_clean(request.source_type) or "text",
        capture_source=_clean(request.capture_source) or "manual",
        created_at=now,
        updated_at=now,
    )


@router.post(
    "/decisions/create-preview",
    response_model=DecisionCreatePreviewResponse,
)
def preview_decision_create(request: DecisionCreatePreviewRequest):
    from app.repositories.sheets_decision_repository import SheetsDecisionRepository

    repo = SheetsDecisionRepository()
    inspection = repo.inspect_schema()
    preview_decision = _preview_item(request)

    if not inspection["exists"] or inspection["headers_match"] is not True:
        warnings = list(inspection["warnings"])
        warnings.append("Decisions schema must exist with approved headers before decisions can be created.")
        return DecisionCreatePreviewResponse(
            dry_run=True,
            would_create_decision=False,
            schema_ok=False,
            duplicate_candidates=[],
            decision=preview_decision,
            warnings=warnings,
        )

    duplicate_candidates = repo.find_duplicate_candidates(
        preview_decision.decision,
        preview_decision.project,
    )
    warnings = []

    if duplicate_candidates:
        warnings.append("Possible duplicate decision found. Preview only; no decision was created.")

    return DecisionCreatePreviewResponse(
        dry_run=True,
        would_create_decision=True,
        schema_ok=True,
        duplicate_candidates=duplicate_candidates,
        decision=preview_decision,
        warnings=warnings,
    )


@router.post(
    "/decisions/create",
    response_model=DecisionCreateResponse,
)
def create_decision(request: DecisionCreateRequest):
    if request.confirmation != CREATE_DECISION_CONFIRMATION:
        return JSONResponse(
            status_code=400,
            content=DecisionCreateResponse(
                created=False,
                schema_ok=False,
                duplicate_candidates=[],
                decision=_preview_item(request),
                warnings=[
                    "Exact confirmation phrase is required. No decision was created.",
                ],
            ).model_dump(),
        )

    from app.repositories.sheets_decision_repository import SheetsDecisionRepository

    repo = SheetsDecisionRepository()
    inspection = repo.inspect_schema()
    decision = _created_item(request)

    if not inspection["exists"] or inspection["headers_match"] is not True:
        warnings = list(inspection["warnings"])
        warnings.append("Decisions schema must exist with approved headers before decisions can be created.")
        return JSONResponse(
            status_code=400,
            content=DecisionCreateResponse(
                created=False,
                schema_ok=False,
                duplicate_candidates=[],
                decision=decision,
                warnings=warnings,
            ).model_dump(),
        )

    duplicate_candidates = repo.find_duplicate_candidates(
        decision.decision,
        decision.project,
    )
    warnings = []

    if duplicate_candidates:
        warnings.append("Possible duplicate decision found. Decision was created anyway.")

    result = repo.create_decision(decision.model_dump())
    warnings.extend(result["warnings"])

    return DecisionCreateResponse(
        created=result["created"],
        schema_ok=result["schema_ok"],
        duplicate_candidates=duplicate_candidates,
        decision=result["decision"],
        warnings=warnings,
    )


@router.post(
    "/decisions/update",
    response_model=DecisionUpdateResponse,
)
def update_decision(request: DecisionUpdateRequest):
    from app.repositories.sheets_decision_repository import SheetsDecisionRepository

    repo = SheetsDecisionRepository()
    provided_fields = getattr(
        request,
        "model_fields_set",
        getattr(request, "__fields_set__", set()),
    )

    fields = {
        field: getattr(request, field)
        for field in provided_fields
        if field != "decision_id"
    }

    updated, decision, warnings = repo.update_decision(
        decision_id=request.decision_id,
        fields=fields,
    )

    return DecisionUpdateResponse(
        updated=updated,
        decision=decision,
        warnings=warnings,
    )


@router.get(
    "/decisions/search",
    response_model=DecisionSearchResponse,
)
def search_decisions(
    query: str = Query(default=""),
    status: str = Query(default=""),
    project: str = Query(default=""),
    importance: str = Query(default=""),
    limit: int = Query(default=50),
):
    from app.repositories.sheets_decision_repository import SheetsDecisionRepository

    repo = SheetsDecisionRepository()
    result = repo.search_decisions(
        query=query,
        status=status,
        project=project,
        importance=importance,
        limit=limit,
    )
    safe_limit = min(max(int(limit or 50), 1), 100)

    return DecisionSearchResponse(
        query=query,
        status=status,
        project=project,
        importance=importance,
        limit=safe_limit,
        count=len(result["decisions"]),
        decisions=result["decisions"],
        warnings=result["warnings"],
    )
