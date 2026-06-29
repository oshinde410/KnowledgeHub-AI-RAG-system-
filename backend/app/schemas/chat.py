from typing import Optional

from pydantic import BaseModel


class SourceItem(BaseModel):
    document_id: str
    score: float
    text: str


class ChatRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None
    # Optional explicit document scope for this request (session-scoped)
    document_ids: list[str] = []
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    sources: list[SourceItem]
