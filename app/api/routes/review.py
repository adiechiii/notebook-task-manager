from fastapi import APIRouter

from app.services.weekly_review_service import build_weekly_review

router = APIRouter()


@router.get("/review/weekly")
def get_weekly_review():
    return build_weekly_review()
