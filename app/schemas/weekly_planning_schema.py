from typing import Any

from pydantic import BaseModel


class WeeklyPlanningResponse(BaseModel):
    dry_run: bool
    writes: bool
    generated_at: str
    scope: dict[str, Any]
    summary: dict[str, Any]
    weekly_plan: dict[str, Any]
    focus_areas: list[dict[str, Any]]
    priority_tasks: list[dict[str, Any]]
    project_plans: list[dict[str, Any]]
    decision_followups: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    cognition_priorities: list[dict[str, Any]]
    recommended_actions: list[dict[str, Any]]
    evidence: dict[str, Any]
    signals_used: list[str]
    warnings: list[str]
