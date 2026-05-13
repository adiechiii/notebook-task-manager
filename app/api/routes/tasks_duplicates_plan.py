from fastapi import APIRouter

from app.services.duplicate_cleanup_plan_service import build_duplicate_cleanup_plan

router = APIRouter()


@router.get("/tasks/duplicates-plan", operation_id="getDuplicateTasksPlan")
def get_duplicate_tasks_plan():
    return build_duplicate_cleanup_plan()
