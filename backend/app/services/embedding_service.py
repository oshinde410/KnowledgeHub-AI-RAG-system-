from __future__ import annotations

from typing import Any
from app.core.config import settings

GEMINI_EMBEDDING_MODEL = "gemini-embedding-001"
EMBEDDING_DIMENSION_LOCAL = 384

_model: Any | None = None


def _get_model():
    """Lazy-load the SentenceTransformer model.

    This is a fallback only. If `OPENAI_API_KEY` is configured in settings,
    the service will call OpenAI embeddings instead to avoid importing
    heavyweight ML libraries into the web process.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        # Keep the same model for compatibility.
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_embedding_dimension():
    return 3072 if settings.GEMINI_API_KEY else EMBEDDING_DIMENSION_LOCAL


def get_embedding_collection_name():
    return f"document_chunks_{get_embedding_dimension()}"


def _gemini_embedding(text: str):
    import json
    import urllib.parse
    import urllib.request

    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not configured")

    url = (
        f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_EMBEDDING_MODEL}:embedContent"
        f"?key={urllib.parse.quote(settings.GEMINI_API_KEY)}"
    )
    payload = {
        "model": "models/" + GEMINI_EMBEDDING_MODEL,
        "content": {"parts": [{"text": text}]},
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    embedding = data.get("embedding", {}).get("values")
    if not embedding:
        raise RuntimeError("Gemini embedding response did not contain values")
    return embedding


def create_embedding(text: str):
    # If a Gemini API key is present, prefer remote embeddings to keep the
    # web process small. This avoids importing torch/transformers in the web
    # process which can push memory above 512MB.
    if settings.GEMINI_API_KEY:
        return _gemini_embedding(text)

    # Delegate embedding computation to a Celery worker so the web
    # process never needs to load heavy ML libraries. If Celery isn't
    # available, do NOT fall back to importing the local model here —
    # importing `sentence_transformers` in the web process can push memory
    # usage above Render's 512MB limit. Instead raise a clear error so the
    # deploy can be fixed (start a worker or set `OPENAI_API_KEY`).
    try:
        # import here to keep top-level imports light in the web process
        from app.celery_app import celery_app

        async_result = celery_app.send_task("app.tasks.compute_embedding_task", args=[text])
        # Wait briefly for worker result; if worker not running this will raise/timeout.
        return async_result.get(timeout=20)
    except Exception as exc:
        raise RuntimeError(
            "Embedding worker not available. Start the Celery worker or set GEMINI_API_KEY in environment. "
            f"(original error: {exc})"
        )

