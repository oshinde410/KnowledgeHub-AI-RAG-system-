import uuid

from sqlalchemy.orm import Session

from app.models.processing_job import ProcessingJob



def create_processing_job(db: Session, document_id: str) -> ProcessingJob:
    job = ProcessingJob(
        id=str(uuid.uuid4()),
        document_id=document_id,
        status="PENDING",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def list_processing_jobs(db: Session):
    return (
        db.query(ProcessingJob)
        .order_by(ProcessingJob.created_at.desc())
        .all()
    )


def get_processing_job(db: Session, job_id: str):
    return (
        db.query(ProcessingJob)
        .filter(ProcessingJob.id == job_id)
        .first()
    )
