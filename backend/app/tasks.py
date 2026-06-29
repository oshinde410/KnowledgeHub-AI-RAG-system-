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
