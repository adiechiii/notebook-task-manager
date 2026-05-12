from fastapi import APIRouter, Query

from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.schemas.memory_schema import MemoryCreateRequest
from app.services.memory_classification_service import classify_memory
from app.services.project_linking_service import resolve_project

router = APIRouter()
repo = SheetsMemoryRepository()


@router.post("/memory/create")
def create_memory(request: MemoryCreateRequest):
    classification = classify_memory(request.text)
    resolved_project = resolve_project(request.text, request.project or "")
    if resolved_project:
        classification["project"] = resolved_project

    memory_id = repo.create_memory(
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


@router.get("/memory/search")
def search_memories(query: str = Query(default="")):
    memories = repo.search_memories(query)
    return {"memories": memories}
