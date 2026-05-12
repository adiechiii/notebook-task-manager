from pydantic import BaseModel


class ArchiveRequest(BaseModel):
    confirm: str
    status: str = "Done"
    older_than_days: int = 0
    include_done: bool = True
