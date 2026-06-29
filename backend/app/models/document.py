from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import BigInteger

from app.db.base import Base



class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)

    file_name = Column(String, nullable=False)

    file_path = Column(String, nullable=False)

    file_type = Column(String, nullable=False)

    file_size = Column(BigInteger)

    status = Column(String)

    uploaded_by = Column(String)

    # Temporary per-page session documents (deleted on session cleanup)
    session_id = Column(String, nullable=True)
