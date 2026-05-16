from typing import Any

from pydantic import BaseModel


class UnifiedDashboardResponse(BaseModel):
    dry_run: bool
    writes: bool
    generated_at: str
    scope: dict[str, Any]
    summary: dict[str, Any]
    focus: dict[str, Any]
    task_buckets: dict[str, Any]
    project_rollups: list[dict[str, Any]]
    decision_context: dict[str, Any]
    memory_context: dict[str, Any]
    blockers: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    execution_progress: dict[str, Any]
    recommendations: list[dict[str, Any]]
    warnings: list[str]
