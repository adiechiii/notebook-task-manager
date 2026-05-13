from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.services.recurring_task_preview_service import build_recurring_task_preview


router = APIRouter()


class RecurringTaskPreviewRequest(BaseModel):
    text: str
    project: str = ""
    timezone: str = "Etc/UTC"
    anchor_date: Optional[str] = None
    horizon_days: int = Field(default=90)


class RecurringTaskPreviewRule(BaseModel):
    title: str
    frequency: str
    interval: int
    days_of_week: list[str]
    day_of_month: Optional[int] = None
    month_of_year: Optional[int] = None
    start_date: str
    category: str
    priority: str
    project: str
    timezone: str


class RecurringTaskPreviewOccurrence(BaseModel):
    due_date: str
    task_title: str
    would_create_task: bool


class RecurringTaskPreviewMetadata(BaseModel):
    anchor_date: str
    horizon_days: int
    preview_only: bool


class RecurringTaskPreviewResponse(BaseModel):
    dry_run: bool
    creates_tasks: bool
    schema_changes: bool
    recurring_task: RecurringTaskPreviewRule
    occurrences: list[RecurringTaskPreviewOccurrence]
    warnings: list[str]
    metadata: RecurringTaskPreviewMetadata


@router.post("/recurring-tasks/preview", response_model=RecurringTaskPreviewResponse)
def preview_recurring_task(request: RecurringTaskPreviewRequest):
    return build_recurring_task_preview(
        text=request.text,
        project=request.project,
        timezone=request.timezone,
        anchor_date=request.anchor_date,
        horizon_days=request.horizon_days,
    )
