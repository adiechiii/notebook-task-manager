from fastapi import APIRouter

from app.schemas.system_schema import ContextHealthResponse, SuggestedFixesResponse
from app.services.context_health_service import build_context_health, build_suggested_fixes

router = APIRouter()


@router.get("/system/context-health", response_model=ContextHealthResponse)
def get_context_health():
    return ContextHealthResponse(**build_context_health())


@router.get("/system/suggested-fixes", response_model=SuggestedFixesResponse)
def get_suggested_fixes():
    return SuggestedFixesResponse(**build_suggested_fixes())
