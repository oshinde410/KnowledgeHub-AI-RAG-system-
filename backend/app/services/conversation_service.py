import uuid

from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.message import Message


def create_conversation(
    db: Session,
    user_id: str,
    title: str,
    conversation_id: str | None = None,
):

    conversation = Conversation(
        id=str(conversation_id or uuid.uuid4()),
        user_id=user_id,
        title=title,
    )


    db.add(conversation)
    db.commit()
    db.refresh(conversation)

    return conversation


def get_conversation(
    db: Session,
    conversation_id: str,
    user_id: str | None = None
):
    print("\n=== CONVERSATION LOOKUP ===")
    print("requested id:", conversation_id)
    print("requested user:", user_id)

    query = db.query(Conversation).filter(
        Conversation.id == conversation_id
    )

    if user_id:
        query = query.filter(
            Conversation.user_id == user_id
        )

    conversation = query.first()

    print("result:", conversation)

    if not conversation:
        all_conversations = (
            db.query(Conversation)
            .all()
        )

        print("\nAvailable conversations:")
        for c in all_conversations:
            print(
                c.id,
                c.user_id
            )

    print("=========================\n")

    return conversation


def list_conversations(db: Session, user_id: str):
    return (
        db.query(Conversation)
        .filter(Conversation.user_id == user_id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )


def list_messages(db: Session, conversation_id: str, user_id: str):
    conversation = get_conversation(db, conversation_id, user_id=user_id)
    if not conversation:
        return None

    return (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(Message.created_at.asc())
        .all()
    )


def save_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    sources=None
):

    message = Message(
        id=str(uuid.uuid4()),
        conversation_id=conversation_id,
        role=role,
        content=content,
        retrieved_sources=sources,
        token_count=len(content.split())
    )

    db.add(message)
    db.commit()

    return message
