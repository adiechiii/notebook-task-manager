from fastapi import APIRouter, Query

from app.schemas.smart_priority_schema import SmartPrioritiesResponse
from app.services.smart_priority_service import build_smart_priorities

router = APIRouter()


@router.get("/priorities/smart", response_model=SmartPrioritiesResponse, operation_id="getSmartPriorities")
def get_smart_priorities(
    project: str = Query(default=""),
    limit: int = Query(default=10),
):
    return SmartPrioritiesResponse(
        **build_smart_priorities(
            project=project,
            limit=limit,
        )
    )
