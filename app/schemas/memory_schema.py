from pydantic import BaseModel, Field


class MemoryCreateRequest(BaseModel):
    text: str
    project: str = ""

class MemoryUpdateRequest(BaseModel):
    memory_id: str
    memory_summary: str | None = None
    memory_type: str | None = None
    entity: str | None = None
    project: str | None = None
    tags: str | None = None
    importance: str | None = None
    status: str | None = None


class MemoryResponse(BaseModel):
    memory_id: str | None = None
    text: str | None = None
    summary: str | None = None
    type: str | None = None
    entity: str | None = None
    project: str | None = None
    tags: str | None = None
    importance: str | None = None
    status: str | None = None
    updated_at: str | None = None


class MemoryUpdateResponse(BaseModel):
    updated: bool
    memory: MemoryResponse | None = None
    warnings: list[str] = Field(default_factory=list)
