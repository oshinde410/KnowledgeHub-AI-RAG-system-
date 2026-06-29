from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import Depends
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.api.deps import get_db

from app.api.deps_auth import get_current_user

from app.services.document_service import save_document
from app.services.document_service import delete_document
from app.services.job_service import create_processing_job
from app.services.job_service import list_processing_jobs
from app.tasks import process_document_task
from app.models.document import Document
from app.models.document_content import DocumentContent
from app.models.document_chunk import DocumentChunk


router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

@router.post("/upload")
def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
    session_id: str | None = None,
):
    try:
        document = save_document(
            db=db,
            file=file,
            user_id=user.id,
            session_id=session_id,
        )


        job = create_processing_job(
            db,
            document.id
        )

        process_document_task.delay(
            document.id,
            job.id
        )

        return {
            "message": "Upload successful",
            "document_id": document.id,
            "job_id": job.id,
            "status": "PENDING"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    
@router.get("")
def list_documents(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    documents = (
        db.query(Document)
        .all()
    )

    return documents


@router.get("/jobs")
def processing_jobs(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return list_processing_jobs(db)


@router.delete("/{document_id}")
def remove_document(
    document_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    deleted = delete_document(db, document_id)

    if not deleted:
        raise HTTPException(
            status_code=404,
            detail="Document not found"
        )

    return {
        "message": "Document deleted",
        "document_id": document_id
    }

@router.get("/search")
def search_documents(
    q: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    documents = (
        db.query(Document)
        .filter(
            Document.file_name.ilike(
                f"%{q}%"
            )
        )
        .all()
    )

    return documents

@router.get("/{document_id}/content")
def document_content(
    document_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    content = (
        db.query(DocumentContent)
        .filter(
            DocumentContent.document_id
            == document_id
        )
        .first()
    )

    if not content:
        return {
            "message": "No content"
        }

    return {
        "content": content.content
    }

@router.get("/{document_id}/chunks")
def get_chunks(
    document_id: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):

    chunks = (
        db.query(DocumentChunk)
        .filter(
            DocumentChunk.document_id
            == document_id
        )
        .all()
    )

    return chunks
