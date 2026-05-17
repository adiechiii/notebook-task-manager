from pydantic import BaseModel, Field

class UpdateRequest(BaseModel):
    text: str
    status: str

class TaskBulkUpdateItem(BaseModel):
    task_id: str
    status: str | None = None
    priority: str | None = None
    category: str | None = None
    project: str | None = None
    page_date: str | None = None


class TaskBulkUpdateRequest(BaseModel):
    updates: list[TaskBulkUpdateItem]


class TaskBulkUpdateResponseItem(BaseModel):
    task_id: str | None = None
    text: str | None = None
    title: str | None = None
    status: str | None = None
    page_date: str | None = None
    category: str | None = None
    priority: str | None = None
    project: str | None = None
    updated_at: str | None = None
    completion_date: str | None = None


class TaskBulkUpdateResponse(BaseModel):
    updated_count: int
    updated_tasks: list[TaskBulkUpdateResponseItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
