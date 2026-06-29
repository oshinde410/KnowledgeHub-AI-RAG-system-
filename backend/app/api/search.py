from fastapi import APIRouter
from app.services.retrieval_service import retrieve_context

router = APIRouter(
    prefix="/search",
    tags=["Search"]
)

@router.get("")
def search(
    query: str
):

    return retrieve_context(query)