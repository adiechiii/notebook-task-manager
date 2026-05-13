from fastapi import APIRouter

from app.services.duplicate_cleanup_preview_service import build_duplicate_tasks_preview

router = APIRouter()


@router.get("/tasks/duplicates-preview")
def get_duplicate_tasks_preview():
    return build_duplicate_tasks_preview()
