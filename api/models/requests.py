from typing import Literal
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    session_id: str
    question: str = Field(min_length=1)
    search_type: Literal["keyword", "semantic", "hybrid"] = "hybrid"
    top_k: int = Field(default=5, ge=1, le=50)
    model_type: Literal["openai", "ollama"] = "openai"
