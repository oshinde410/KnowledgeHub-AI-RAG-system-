from fastapi import APIRouter
from fastapi import Depends

from app.api.deps_auth import get_current_user


router = APIRouter(
    tags=["Users"]
)


@router.get("/me")
def me(
    user=Depends(get_current_user)
):
    return {
        "id": user.id,
        "email": user.email,
        "role": user.role
    }