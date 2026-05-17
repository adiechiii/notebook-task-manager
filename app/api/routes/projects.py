from fastapi import APIRouter, Query

from app.repositories.sheets_project_repository import SheetsProjectRepository
from app.schemas.project_schema import ProjectCreateRequest, ProjectUpdateRequest, ProjectUpdateResponse
from app.services.project_dashboard_service import build_project_dashboard

router = APIRouter()
repo = SheetsProjectRepository()


@router.post("/projects/create")
def create_project(request: ProjectCreateRequest):
    project_id = repo.create_project(
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

    updated, project, warnings = repo.update_project(
        name=request.name,
        fields=fields,
    )

    return {
        "updated": updated,
        "project": project,
        "warnings": warnings,
    }


@router.get("/projects/search")
def search_projects(query: str = Query(default="")):
    projects = repo.search_projects(query)
    return {"projects": projects}


@router.get("/projects/dashboard")
def get_project_dashboard(
    query: str = Query(default=""),
    include_details: bool = Query(default=False),
):
    return build_project_dashboard(query, include_details=include_details)
