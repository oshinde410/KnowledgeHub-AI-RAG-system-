import uuid

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_response_log import AIResponseLog
from app.models.retrieval_log import RetrievalLog


def log_retrieval(
    db: Session,
    query_text: str,
    top_k: int,
    retrieval_latency_ms: int,
    message_id: str | None = None,
):
    log = RetrievalLog(
        id=str(uuid.uuid4()),
        message_id=message_id,
        query_text=query_text,
        top_k=top_k,
        retrieval_latency_ms=retrieval_latency_ms,
    )
    db.add(log)
    db.commit()
    return log


def log_ai_response(
    db: Session,
    prompt: str,
    answer: str,
    generation_time_ms: int,
    message_id: str | None = None,
):
    log = AIResponseLog(
        id=str(uuid.uuid4()),
        message_id=message_id,
        model_name=settings.OLLAMA_MODEL,
        prompt_tokens=len(prompt.split()),
        completion_tokens=len(answer.split()),
        generation_time_ms=generation_time_ms,
    )
    db.add(log)
    db.commit()
    return log
