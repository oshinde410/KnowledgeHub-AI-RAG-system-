from sqlalchemy import Column
from sqlalchemy import String

from app.db.base import Base



class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True)

    email = Column(String, unique=True, nullable=False)

    password_hash = Column(String, nullable=False)

    full_name = Column(String, nullable=False)

    role = Column(String, nullable=False)