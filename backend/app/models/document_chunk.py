from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Text

from app.db.base import Base



class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(String, primary_key=True)

    document_id = Column(
        String,
        nullable=False
    )

    chunk_index = Column(
        String,
        nullable=False
    )

    content = Column(
        Text,
        nullable=False
    )