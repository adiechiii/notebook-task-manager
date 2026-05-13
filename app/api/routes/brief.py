from fastapi import APIRouter

from app.services.morning_brief_service import build_morning_brief

router = APIRouter()


@router.get("/brief/morning")
def get_morning_brief():
    return build_morning_brief()
