from pydantic import BaseModel, Field


class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""

class ProjectUpdateRequest(BaseModel):
    name: str
    priority: str | None = None
    category: str | None = None
    description: str | None = None
    goal: str | None = None
    tags: str | None = None
    status: str | None = None

class ProjectResponse(BaseModel):
    name: str | None = None
    priority: str | None = None
    category: str | None = None
    description: str | None = None
    goal: str | None = None
    tags: str | None = None
    status: str | None = None
    updated_at: str | None = None


class ProjectUpdateResponse(BaseModel):
    updated: bool
    project: ProjectResponse | None = None
    warnings: list[str] = Field(default_factory=list)

class StaleProjectResponseItem(ProjectResponse):
    age_days: int | None = None
    reason: str


class StaleProjectsResponse(BaseModel):
    stale_after_days: int
    count: int
    projects: list[StaleProjectResponseItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
