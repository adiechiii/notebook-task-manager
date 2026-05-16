from typing import Any

from pydantic import BaseModel


class SmartPrioritiesResponse(BaseModel):
    dry_run: bool
    writes: bool
    generated_at: str
    scope: dict[str, Any]
    summary: dict[str, Any]
    ranked_tasks: list[dict[str, Any]]
    decision_context: dict[str, Any]
    project_context: dict[str, Any]
    blockers: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    signals_used: list[str]
    future_signals: list[str]
    warnings: list[str]
