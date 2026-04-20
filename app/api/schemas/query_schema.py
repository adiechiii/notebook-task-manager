from pydantic import BaseModel
from typing import Optional

class QueryRequest(BaseModel):
    status: Optional[str] = None
    category: Optional[str] = None
    date: Optional[str] = None