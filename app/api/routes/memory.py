from fastapi import APIRouter, Query

from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.schemas.memory_schema import MemoryCreateRequest, MemoryUpdateRequest, MemoryUpdateResponse
from app.services.memory_classification_service import classify_memory
from app.services.project_linking_service import resolve_project

router = APIRouter()


def _get_repo():
    return SheetsMemoryRepository()


@router.post("/memory/create")
def create_memory(request: MemoryCreateRequest):
    classification = classify_memory(request.text)
    resolved_project = resolve_project(request.text, request.project or "")
    if resolved_project:
        classification["project"] = resolved_project

    memory_id = _get_repo().create_memory(
        request.text,
        memory_type=classification["type"],
        entity=classification["entity"],
        project=classification["project"],
        tags=classification["tags"],
        importance=classification["importance"],
    )
    return {
        "saved": request.text,
        "memory_id": memory_id,
        "classification": classification,
    }


@router.post("/memories/update", response_model=MemoryUpdateResponse)
def update_memory(request: MemoryUpdateRequest):
    provided_fields = getattr(
        request,
        "model_fields_set",
        getattr(request, "__fields_set__", set()),
    )

    fields = {
        field: getattr(request, field)
        for field in provided_fields
        if field != "memory_id"
    }

    updated, memory, warnings = _get_repo().update_memory(
        memory_id=request.memory_id,
        fields=fields,
    )

    return {
        "updated": updated,
        "memory": memory,
        "warnings": warnings,
    }


@router.get("/memory/search")
def search_memories(query: str = Query(default="")):
    memories = _get_repo().search_memories(query)
    return {"memories": memories}
