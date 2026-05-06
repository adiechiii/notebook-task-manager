from pydantic import BaseModel


class MemoryCreateRequest(BaseModel):
    text: str
