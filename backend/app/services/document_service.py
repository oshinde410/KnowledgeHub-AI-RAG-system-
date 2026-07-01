import os
import uuid
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_content import DocumentContent
from app.models.processing_job import ProcessingJob
from app.services.qdrant_service import delete_document_vectors



ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".txt": "text/plain",
}


def _safe_filename(filename: str) -> str:
    return Path(filename).name.replace("/", "_").replace("\\", "_")


def save_document(
    db: Session,
    file,
    user_id: str,
    session_id: str | None = None
):

    safe_name = _safe_filename(file.filename or "upload")
    extension = os.path.splitext(safe_name)[1].lower()

    if extension not in ALLOWED_TYPES:
        raise ValueError("Only PDF and TXT allowed")

    content = file.file.read()

    if len(content) > settings.MAX_UPLOAD_SIZE_BYTES:
        raise ValueError("File is too large")

    if not content:
        raise ValueError("Uploaded file is empty")

    content_type = (file.content_type or "").split(";")[0].lower()
    expected_type = ALLOWED_TYPES[extension]
    if content_type and content_type not in {expected_type, "application/octet-stream"}:
        raise ValueError("File type does not match the uploaded content")

    document_id = str(uuid.uuid4())

    folder = (
        "uploads/pdf"
        if extension == ".pdf"
        else "uploads/txt"
    )

    os.makedirs(folder, exist_ok=True)

    path = f"{folder}/{document_id}_{safe_name}"

    with open(path, "wb") as buffer:
        buffer.write(content)

    document = Document(
        id=document_id,
        file_name=safe_name,
        file_path=path,
        file_type=extension,
        file_size=os.path.getsize(path),
        status="UPLOADED",
        uploaded_by=user_id,
        session_id=session_id
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    return document


def delete_document(db: Session, document_id: str):
    document = (
        db.query(Document)
        .filter(Document.id == document_id)
        .first()
    )

    if not document:
        return None

    try:
        delete_document_vectors(document_id)
    except Exception as exc:
        print(
            "[document_service] delete_document_vectors failed, continuing document cleanup:",
            repr(exc)
        )

    db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).delete(synchronize_session=False)
    db.query(DocumentContent).filter(
        DocumentContent.document_id == document_id
    ).delete(synchronize_session=False)
    db.query(ProcessingJob).filter(
        ProcessingJob.document_id == document_id
    ).delete(synchronize_session=False)

    if document.file_path and os.path.exists(document.file_path):
        os.remove(document.file_path)

    db.delete(document)
    db.commit()

    return document
