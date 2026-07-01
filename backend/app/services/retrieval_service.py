from sqlalchemy.orm import Session

from app.services.embedding_service import create_embedding
from app.services.qdrant_service import search_chunks
from app.models.document import Document


def retrieve_context(
    db: Session,
    query: str,
    document_ids: list[str] | None = None,
):
    try:
        vector = create_embedding(query)
        results = search_chunks(vector, document_ids=document_ids)
    except Exception as exc:
        print("[retrieval] retrieval failed:", repr(exc))
        return []

    # Prefetch document names for all hits we got back.
    hit_doc_ids = {
        hit.payload.get("document_id")
        for hit in results.points
        if hit.payload.get("document_id") is not None
    }

    doc_name_by_id = {
        d.id: d.file_name
        for d in (db.query(Document).filter(Document.id.in_(hit_doc_ids)).all() if hit_doc_ids else [])
    }

    contexts = []

    for hit in results.points:
        doc_id = hit.payload.get("document_id")
        contexts.append({
            "score": hit.score,
            "text": hit.payload.get("chunk_text"),
            "document_id": doc_id,
            "document_name": doc_name_by_id.get(doc_id),
        })

    return contexts
