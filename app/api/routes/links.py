from fastapi import APIRouter, Query

from app.schemas.link_schema import LinkReviewResponse
from app.services.link_review_service import build_link_review

router = APIRouter()


@router.get("/links/review", response_model=LinkReviewResponse)
def get_links_review(
    include_valid_links: bool = Query(default=False),
    limit: int = Query(default=50),
    area: str = Query(default="all"),
):
    return LinkReviewResponse(
        **build_link_review(
            include_valid_links=include_valid_links,
            limit=limit,
            area=area,
        )
    )
