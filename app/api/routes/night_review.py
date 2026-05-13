from fastapi import APIRouter

from app.services.night_review_service import build_night_review

router = APIRouter()


@router.get("/review/night")
def get_night_review():
    return build_night_review()
