from typing import Any

from pydantic import BaseModel


class InsightsResponse(BaseModel):
    dry_run: bool
    writes: bool
    generated_at: str
    scope: dict[str, Any]
    summary: dict[str, Any]
    insights: list[dict[str, Any]]
    patterns: list[dict[str, Any]]
    risks: list[dict[str, Any]]
    opportunities: list[dict[str, Any]]
    recommended_actions: list[dict[str, Any]]
    evidence: dict[str, Any]
    signals_used: list[str]
    future_signals: list[str]
    warnings: list[str]
