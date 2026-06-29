from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import Integer
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.sql import func

from app.db.base import Base


class RetrievalLog(Base):
    __tablename__ = "retrieval_logs"

    id = Column(String, primary_key=True)
    message_id = Column(String)
    query_text = Column(Text, nullable=False)
    top_k = Column(Integer, nullable=False)
    retrieval_latency_ms = Column(Integer, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
