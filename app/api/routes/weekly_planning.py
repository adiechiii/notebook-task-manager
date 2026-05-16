from fastapi import APIRouter, Query

from app.schemas.weekly_planning_schema import WeeklyPlanningResponse
from app.services.weekly_planning_service import build_weekly_planning

router = APIRouter()


@router.get("/planning/weekly", response_model=WeeklyPlanningResponse, operation_id="getWeeklyPlanning")
def get_weekly_planning(
    project: str = Query(default=""),
    limit: int = Query(default=10),
):
    return WeeklyPlanningResponse(
        **build_weekly_planning(
            project=project,
            limit=limit,
        )
    )
