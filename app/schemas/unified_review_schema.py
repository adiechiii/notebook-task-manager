from typing import Any

from pydantic import BaseModel


class UnifiedReviewResponse(BaseModel):
    dry_run: bool
    writes: bool
    generated_at: str
    scope: dict[str, Any]
    summary: dict[str, Any]
    progress: dict[str, Any]
    unfinished_work: dict[str, Any]
    decisions: dict[str, Any]
    memories: dict[str, Any]
    blockers: list[dict[str, Any]]
    patterns: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    recommended_focus: list[dict[str, Any]]
    carryover: list[dict[str, Any]]
    period_review: dict[str, Any]
    warnings: list[str]
