from fastapi import APIRouter, Query

from app.schemas.insight_schema import InsightsResponse
from app.services.insight_service import build_insights

router = APIRouter()


@router.get("/insights", response_model=InsightsResponse, operation_id="getInsights")
def get_insights(
    project: str = Query(default=""),
    limit: int = Query(default=10),
):
    return InsightsResponse(
        **build_insights(
            project=project,
            limit=limit,
        )
    )
