from pydantic import BaseModel

class IngestRequest(BaseModel):
    text: str