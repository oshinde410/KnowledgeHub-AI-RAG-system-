import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.document import Document

from app.models.document_content import DocumentContent

from app.models.processing_job import ProcessingJob

from app.services.parser_service import extract_pdf_text, extract_txt_text

from app.models.document_chunk import DocumentChunk

from app.services.chunking_service import chunk_text
from app.services.embedding_service import create_embedding
from app.services.qdrant_service import insert_chunk


def process_document(
    db: Session,
    document: Document,
    job_id: str | None = None
):
    job = None
    if job_id:
        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.id == job_id)
            .first()
        )

    try:
        document.status = "PROCESSING"
        if job:
            job.status = "RUNNING"
            job.started_at = datetime.now(timezone.utc)
        db.commit()

        if document.file_type == ".pdf":
            text = extract_pdf_text(document.file_path)
        else:
            text = extract_txt_text(document.file_path)

        db.query(DocumentContent).filter(
            DocumentContent.document_id == document.id
        ).delete(synchronize_session=False)
        db.query(DocumentChunk).filter(
            DocumentChunk.document_id == document.id
        ).delete(synchronize_session=False)

        db.add(
            DocumentContent(
                id=str(uuid.uuid4()),
                document_id=document.id,
                content=text
            )
        )

        chunks = chunk_text(text)

        for index, chunk in enumerate(chunks):
            db_chunk = DocumentChunk(
                id=str(uuid.uuid4()),
                document_id=document.id,
                chunk_index=str(index),
                content=chunk
            )

            db.add(db_chunk)
            vector = create_embedding(chunk)
            insert_chunk(
                chunk_id=db_chunk.id,
                document_id=document.id,
                chunk_text=chunk,
                vector=vector
            )

            vector = create_embedding(chunk)

            print("VECTOR TYPE:", type(vector))
            print("VECTOR LENGTH:", len(vector) if vector else None)

        document.status = "INDEXED"
        if job:
            job.status = "COMPLETED"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = None

        db.commit()
        return True

    except Exception as exc:
        document.status = "FAILED"
        if job:
            job.status = "FAILED"
            job.completed_at = datetime.now(timezone.utc)
            job.error_message = str(exc)
        db.commit()
        raise
