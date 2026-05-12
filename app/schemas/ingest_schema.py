from pydantic import BaseModel
from typing import List

class IngestRequest(BaseModel):
    text: str
    project: str = ""
