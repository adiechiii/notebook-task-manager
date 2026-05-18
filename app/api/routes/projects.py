from fastapi import APIRouter, Query

from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.schemas.project_schema import ProjectCreateRequest, ProjectUpdateRequest, ProjectUpdateResponse, StaleProjectsResponse
from app.services.project_dashboard_service import build_project_dashboard

router = APIRouter()


def _get_repo():
    return SheetsProjectRepository()


@router.post("/projects/create")
def create_project(request: ProjectCreateRequest):
    project_id = _get_repo().create_project(
        name=request.name,
        description=request.description,
    )

    return {
        "saved": request.name,
        "project_id": project_id,
    }


@router.post("/projects/update", response_model=ProjectUpdateResponse)
def update_project(request: ProjectUpdateRequest):
    provided_fields = getattr(
        request,
        "model_fields_set",
        getattr(request, "__fields_set__", set()),
    )

    fields = {
        field: getattr(request, field)
        for field in provided_fields
        if field != "name"
    }

    updated, project, warnings = _get_repo().update_project(
        name=request.name,
        fields=fields,
    )

    return {
        "updated": updated,
        "project": project,
        "warnings": warnings,
    }




@router.get("/projects/stale", response_model=StaleProjectsResponse)
def get_stale_projects(stale_after_days: int = Query(default=30)):
    projects, warnings = _get_repo().get_stale_projects(
        stale_after_days=stale_after_days,
        statuses={"active", "paused"},
    )

    return StaleProjectsResponse(
        stale_after_days=max(int(stale_after_days or 30), 1),
        count=len(projects),
        projects=projects,
        warnings=warnings,
    )

@router.get("/projects/search")
def search_projects(query: str = Query(default="")):
    projects = _get_repo().search_projects(query)
    return {"projects": projects}


@router.get("/projects/dashboard")
def get_project_dashboard(
    query: str = Query(default=""),
    include_details: bool = Query(default=False),
):
    return build_project_dashboard(query, include_details=include_details)
