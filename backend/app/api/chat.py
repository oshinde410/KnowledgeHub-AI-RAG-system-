from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
import traceback
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user

from app.schemas.chat import ChatRequest
from app.schemas.chat import ChatResponse

from app.services.conversation_service import (
    list_conversations,
    list_messages
)
from app.services.chat_service import ask_chat
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.document import Document
from app.services.document_service import delete_document

import uuid

router = APIRouter(
    prefix="/chat",
    tags=["Chat"]
)


@router.post("/session")
def create_session(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    session_id = str(uuid.uuid4())

    conversation = Conversation(
        id=str(uuid.uuid4()),
        user_id=user.id,
        title="New chat",
        session_id=session_id,
    )
    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return {
        "session_id": session_id,
        "conversation_id": conversation.id
    }


@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # delete all conversation messages for this session
    db.query(Message).filter(
        Message.session_id == session_id
    ).delete(synchronize_session=False)

    # delete all conversations for this session
    db.query(Conversation).filter(
        Conversation.session_id == session_id
    ).delete(synchronize_session=False)

    # delete documents + vectors via existing delete_document
    docs = db.query(Document).filter(Document.session_id == session_id).all()
    for doc in docs:
        delete_document(db, doc.id)

    db.commit()

    return {"message": "Session deleted", "session_id": session_id}




@router.post("/ask", response_model=ChatResponse)
def ask(
    request: ChatRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    print("REQUEST BODY:", request.model_dump())
    try:
        return ask_chat(db, user.id, request)

    except ValueError as exc:
        print("ValueError in /chat/ask:")
        print(str(exc))
        traceback.print_exc()

        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )



@router.get("/conversations")
def conversations(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return list_conversations(db, user.id)


@router.get("/conversations/{conversation_id}/messages")
def conversation_messages(
    conversation_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    messages = list_messages(db, conversation_id, user.id)
    if messages is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return messages
