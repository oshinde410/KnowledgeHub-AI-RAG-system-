from app.celery_app import celery_app

from app.db.session import SessionLocal
from app.models.document import Document
from app.services.processing_service import process_document



@celery_app.task(name="app.tasks.process_document_task")
def process_document_task(document_id: str, job_id: str):
    db = SessionLocal()
    try:
        document = (
            db.query(Document)
            .filter(Document.id == document_id)
            .first()
        )
        if not document:
            raise ValueError("Document not found")
        process_document(db, document, job_id=job_id)
    finally:
        db.close()


# Embedding task: compute embeddings in the Celery worker to avoid loading
# heavy ML libraries in the web process. The worker process will cache the
# model instance in-module so it isn't reloaded per-task.
_embedding_model = None

def _get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer
        _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    return _embedding_model


@celery_app.task(name="app.tasks.compute_embedding_task")
def compute_embedding_task(text: str):
    model = _get_embedding_model()
    return model.encode(text).tolist()
