from pydantic import BaseModel, Field


class SheetHealth(BaseModel):
    name: str
    exists: bool
    headers_match: bool | None = None
    row_count: int = 0
    missing_id_count: int = 0
    duplicate_ids: list[str] = Field(default_factory=list)
    missing_required_fields: dict[str, int] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class ContextHealthResponse(BaseModel):
    ok: bool
    checked_sheets: list[SheetHealth] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
