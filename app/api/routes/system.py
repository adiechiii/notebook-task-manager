from fastapi import APIRouter

from app.schemas.system_schema import ContextHealthResponse
from app.services.context_health_service import build_context_health

router = APIRouter()


@router.get("/system/context-health", response_model=ContextHealthResponse)
def get_context_health():
    return ContextHealthResponse(**build_context_health())
