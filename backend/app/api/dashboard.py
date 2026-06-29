from sqlalchemy import func
from fastapi import APIRouter
from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.api.deps_auth import get_current_user
from app.models.ai_response_log import AIResponseLog
from app.models.conversation import Conversation
from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.processing_job import ProcessingJob
from app.models.retrieval_log import RetrievalLog

router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"]
)


@router.get("/metrics")
def metrics(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    average_generation_ms = (
        db.query(func.avg(AIResponseLog.generation_time_ms))
        .scalar()
        or 0
    )
    average_retrieval_ms = (
        db.query(func.avg(RetrievalLog.retrieval_latency_ms))
        .scalar()
        or 0
    )

    return {
        "total_documents": db.query(Document).count(),
        "indexed_documents": db.query(Document).filter(Document.status == "INDEXED").count(),
        "failed_documents": db.query(Document).filter(Document.status == "FAILED").count(),
        "total_chunks": db.query(DocumentChunk).count(),
        "total_conversations": db.query(Conversation).count(),
        "processing_jobs": db.query(ProcessingJob).count(),
        "average_generation_ms": round(float(average_generation_ms), 2),
        "average_retrieval_ms": round(float(average_retrieval_ms), 2),
    }


@router.get("/jobs")
def jobs(
    db: Session = Depends(get_db),
    user=Depends(get_current_user)
):
    return (
        db.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .all()
    )
