from pydantic import BaseModel, Field


class LinkReviewItem(BaseModel):
    area: str
    item_id: str | None = None
    title: str | None = None
    project: str | None = None
    issue_type: str
    message: str


class LinkReviewAreaSummary(BaseModel):
    checked: int = 0
    missing_project_links: int = 0
    invalid_project_links: int = 0
    valid_project_links: int = 0


class LinkReviewSummary(BaseModel):
    projects_available: int = 0
    tasks: LinkReviewAreaSummary = Field(default_factory=LinkReviewAreaSummary)
    memories: LinkReviewAreaSummary = Field(default_factory=LinkReviewAreaSummary)
    decisions: LinkReviewAreaSummary = Field(default_factory=LinkReviewAreaSummary)


class LinkReviewResponse(BaseModel):
    ok: bool
    area: str
    include_valid_links: bool = False
    limit: int = 50
    summary: LinkReviewSummary
    issues: list[LinkReviewItem] = Field(default_factory=list)
    valid_links: list[LinkReviewItem] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
