import uuid

from sqlalchemy.orm import Session

from app.models.user import User
from app.core.security import (

    hash_password,
    verify_password
)


def create_user(
    db: Session,
    email: str,
    password: str,
    full_name: str
):

    user = User(
        id=str(uuid.uuid4()),
        email=email,
        password_hash=hash_password(password),
        full_name=full_name,
        role="SUPPORT_AGENT"
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate_user(
    db: Session,
    email: str,
    password: str
):

    user = (
        db.query(User)
        .filter(User.email == email)
        .first()
    )

    if not user:
        return None

    if not verify_password(
        password,
        user.password_hash
    ):
        return None

    return user