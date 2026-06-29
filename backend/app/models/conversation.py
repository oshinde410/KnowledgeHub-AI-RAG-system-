from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import DateTime
from sqlalchemy.sql import func

from app.db.base import Base



class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True)

    user_id = Column(String, nullable=False)

    title = Column(String)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Temporary per-page session conversations (deleted on session cleanup)
    session_id = Column(String, nullable=True)
