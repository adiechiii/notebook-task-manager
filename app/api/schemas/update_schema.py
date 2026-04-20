from pydantic import BaseModel


class UpdateRequest(BaseModel):
    task_id: str
    status: str