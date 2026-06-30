from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition
from qdrant_client.models import Filter
from qdrant_client.models import MatchAny
from qdrant_client.models import MatchValue
from qdrant_client.models import PointStruct
from qdrant_client.models import FilterSelector

from app.core.config import settings


# Supports both local Qdrant (host/port) and Qdrant Cloud (cluster endpoint + API key).
# Prefer QDRANT_CLUSTER_ENDPOINT when provided.
_client_kwargs: dict = {}
if getattr(settings, "QDRANT_CLUSTER_ENDPOINT", None):
    _client_kwargs.update(
        url=settings.QDRANT_CLUSTER_ENDPOINT,
        api_key=getattr(settings, "QDRANT_API_KEY", None),
    )
else:
    _client_kwargs.update(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
    )

client = QdrantClient(**_client_kwargs)


from qdrant_client.models import (
    Distance,
    VectorParams
)


def create_collection():

    collections = client.get_collections()

    existing = [
        c.name
        for c in collections.collections
    ]

    if "document_chunks" in existing:
        return

    client.create_collection(
        collection_name="document_chunks",
        vectors_config=VectorParams(
            size=384,
            distance=Distance.COSINE
        )
    )

def insert_chunk(
    chunk_id,
    document_id,
    chunk_text,
    vector,
):
    """Insert chunk vector into Qdrant.

    To keep Render free-tier memory/network usage low, we avoid storing the
    full chunk text inside Qdrant payload.

    If you later need chunk text from Qdrant, store only document_id + chunk_id
    and fetch chunk text from Postgres (DocumentChunk table).
    """
    client.upsert(
        collection_name="document_chunks",
        points=[
            PointStruct(
                id=chunk_id,
                vector=vector,
                payload={
                    "document_id": document_id,
                    "chunk_id": chunk_id,
                    # intentionally omit "chunk_text"
                },
            )
        ],
    )

def search_chunks(
    vector,
    limit=5,
    document_ids=None
):
    query_filter = None
    if document_ids:
        query_filter = Filter(
            must=[
                FieldCondition(
                    key="document_id",
                    match=MatchAny(any=document_ids)
                )
            ]
        )

    result = client.query_points(
        collection_name="document_chunks",
        query=vector,
        limit=limit,
        query_filter=query_filter
    )

    return result


def delete_document_vectors(document_id: str):
    client.delete(
        collection_name="document_chunks",
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(
                        key="document_id",
                        match=MatchValue(value=document_id)
                    )
                ]
            )
        )
    )
