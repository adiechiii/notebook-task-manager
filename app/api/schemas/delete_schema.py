from pydantic import BaseModel


class DeleteRequest(BaseModel):
    task_id: str