from pydantic import BaseModel


class ChatSessionCreateResponse(BaseModel):
    session_id: str

