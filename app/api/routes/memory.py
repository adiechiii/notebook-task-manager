from fastapi import APIRouter, Query

from app.repositories.sheets_memory_repository import SheetsMemoryRepository
from app.schemas.memory_schema import MemoryCreateRequest

router = APIRouter()
repo = SheetsMemoryRepository()


@router.post("/memory/create")
def create_memory(request: MemoryCreateRequest):
    memory_id = repo.create_memory(request.text)
    return {
        "saved": request.text,
        "memory_id": memory_id,
    }


@router.get("/memory/search")
def search_memories(query: str = Query(default="")):
    memories = repo.search_memories(query)
    return {"memories": memories}
