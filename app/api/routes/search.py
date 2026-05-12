from fastapi import APIRouter, Query

from app.services.search_service import build_search_everything

router = APIRouter()


@router.get("/search/everything")
def search_everything(query: str = Query(default="")):
    return build_search_everything(query)
