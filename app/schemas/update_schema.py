from pydantic import BaseModel

class UpdateRequest(BaseModel):
    text: str
    status: str