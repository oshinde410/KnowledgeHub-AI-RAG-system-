from app.core.config import settings
from app.services.embedding_service import get_embedding_collection_name


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


_client = None


def _get_client():
    global _client
    if _client is None:
        from qdrant_client import QdrantClient

        _client = QdrantClient(**_client_kwargs)
    return _client


def create_collection():
    """Create Qdrant collection if missing.

    IMPORTANT for Render free tier:
    Qdrant networking may be unavailable during container startup.
    Failing fast here prevents the whole web app from booting.

    We therefore treat startup collection init as best-effort.
    """
    # Optional env to skip initialization entirely.
    import os

    if os.getenv("SKIP_QDRANT_INIT", "false").lower() in {"1", "true", "yes"}:
        return

    try:
        client = _get_client()
        collections = client.get_collections()
        existing = [c.name for c in collections.collections]
        collection_name = get_embedding_collection_name()
        if collection_name in existing:
            return

        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=int(collection_name.split("_")[-1]),
                distance=Distance.COSINE,
            ),
        )
    except Exception as exc:
        # Best-effort logging; never crash app startup due to Qdrant.
        print("[qdrant_service] create_collection skipped due to error:", repr(exc))
        return

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
    from qdrant_client.models import PointStruct

    client = _get_client()
    client.upsert(
        collection_name=get_embedding_collection_name(),
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
    from qdrant_client.models import FieldCondition, Filter, MatchAny

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

    client = _get_client()
    result = client.query_points(
        collection_name=get_embedding_collection_name(),
        query=vector,
        limit=limit,
        query_filter=query_filter
    )

    return result


def delete_document_vectors(document_id: str):
    from qdrant_client.models import FieldCondition, Filter, FilterSelector, MatchValue

    client = _get_client()
    client.delete(
        collection_name=get_embedding_collection_name(),
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
