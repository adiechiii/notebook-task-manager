from fastapi import APIRouter, Query

from app.schemas.unified_review_schema import UnifiedReviewResponse
from app.services.unified_review_service import build_unified_review

router = APIRouter()


@router.get("/review/unified", response_model=UnifiedReviewResponse, operation_id="getUnifiedReview")
def get_unified_review(
    period: str = Query(default="weekly"),
    project: str = Query(default=""),
    limit: int = Query(default=10),
):
    return UnifiedReviewResponse(
        **build_unified_review(
            period=period,
            project=project,
            limit=limit,
        )
    )
