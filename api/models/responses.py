from typing import List, Optional
from pydantic import BaseModel


class UploadResponse(BaseModel):
    session_id: str
    filename: str
    index_name: str
    status: str
    message: str


class SessionInfo(BaseModel):
    session_id: str
    filename: str
    index_name: str
    status: str
    created_at: str
    error: Optional[str] = None


class SessionListResponse(BaseModel):
    sessions: List[SessionInfo]
    total: int


class QueryResponse(BaseModel):
    session_id: str
    question: str
    answer: str
    search_type: str
    model_type: str
