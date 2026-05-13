from fastapi import APIRouter

from app.services.focus_mode_service import build_focus_mode

router = APIRouter()


@router.get("/focus/mode")
def get_focus_mode():
    return build_focus_mode()
