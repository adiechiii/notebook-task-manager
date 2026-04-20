from pydantic import BaseModel

class DeleteRequest(BaseModel):
    text: str