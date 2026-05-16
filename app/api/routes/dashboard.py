from fastapi import APIRouter, Query

from app.schemas.dashboard_schema import UnifiedDashboardResponse
from app.services.unified_dashboard_service import build_unified_dashboard

router = APIRouter()


@router.get("/dashboard/unified", response_model=UnifiedDashboardResponse, operation_id="getUnifiedDashboard")
def get_unified_dashboard(
    project: str = Query(default=""),
    mode: str = Query(default="overview"),
    limit: int = Query(default=10),
):
    return UnifiedDashboardResponse(
        **build_unified_dashboard(
            project=project,
            mode=mode,
            limit=limit,
        )
    )
