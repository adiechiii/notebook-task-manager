from typing import Any

from pydantic import BaseModel


class CapturePreviewRequest(BaseModel):
    text: str
    project: str = ""
    source_type: str = "text"
    capture_source: str = "manual"


class CapturePreviewResponse(BaseModel):
    dry_run: bool
    writes: bool
    recommended_type: str
    confidence: str
    reason: str
    resolved_project: str
    preview: dict[str, Any]
    supported_confirm_endpoint: str
    warnings: list[str]

class CaptureConfirmRequest(BaseModel):
    text: str
    project: str = ""
    recommended_type: str = ""
    source_type: str = "text"
    capture_source: str = "manual"
    confirmation: str


class CaptureConfirmResponse(BaseModel):
    confirmed: bool
    created_type: str
    saved: dict[str, Any]
    warnings: list[str]

