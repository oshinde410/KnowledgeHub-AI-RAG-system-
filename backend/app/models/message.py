from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy import Integer
from sqlalchemy import JSON
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from app.db.base import Base



class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True)

    conversation_id = Column(
        String,
        nullable=False
    )

    role = Column(
        String,
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )

    retrieved_sources = Column(
        JSON
    )

    token_count = Column(
        Integer,
        default=0
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Temporary per-page session messages (deleted on session cleanup)
    session_id = Column(String, nullable=True)
