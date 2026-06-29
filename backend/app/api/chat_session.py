from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException

import uuid
from typing import List

from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user

from app.models.conversation import Conversation
from app.models.message import Message
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_content import DocumentContent
from app.models.processing_job import ProcessingJob
from app.services.qdrant_service import delete_document_vectors

router = APIRouter(prefix="/chat", tags=["Chat Session"])


@router.post("/session")
def create_session(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Stateless session id: we rely on session_id columns for cleanup.
    session_id = str(uuid.uuid4())
    return {"session_id": session_id}


@router.delete("/session/{session_id}")
def delete_session(
    session_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    # Delete documents + their vectors/chunks
    docs = db.query(Document).filter(Document.session_id == session_id).all()
    doc_ids = [d.id for d in docs]

    for document_id in doc_ids:
        delete_document_vectors(document_id)

    db.query(DocumentChunk).filter(DocumentChunk.document_id.in_(doc_ids)).delete(synchronize_session=False)
    db.query(DocumentContent).filter(DocumentContent.document_id.in_(doc_ids)).delete(synchronize_session=False)
    db.query(ProcessingJob).filter(ProcessingJob.document_id.in_(doc_ids)).delete(synchronize_session=False)
    db.query(Document).filter(Document.session_id == session_id).delete(synchronize_session=False)

    # Delete conversations/messages for this session
    conv_ids = [c.id for c in db.query(Conversation).filter(
        Conversation.session_id == session_id,
        Conversation.user_id == user.id
    ).all()]

    if conv_ids:
        db.query(Message).filter(Message.conversation_id.in_(conv_ids)).delete(synchronize_session=False)
        db.query(Conversation).filter(Conversation.id.in_(conv_ids)).delete(synchronize_session=False)

    db.commit()

    return {"message": "Session deleted", "session_id": session_id}

