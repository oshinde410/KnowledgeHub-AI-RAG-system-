from __future__ import annotations

from typing import Any
from app.core.config import settings

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


def _openai_embedding(text: str):
    import json
    import urllib.request

    url = "https://api.openai.com/v1/embeddings"
    payload = {
        "input": text,
        # prefer small embedding model to reduce latency/cost
        "model": "text-embedding-3-small",
    }

    req = urllib.request.Request(
        url=url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
        },
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8")
    data = json.loads(body)
    # OpenAI returns: data[0].embedding as list of floats
    return data[0]["embedding"]


def create_embedding(text: str):
    # If an OpenAI API key is present, prefer remote embeddings to keep the
    # web process small. This avoids importing torch/transformers in the web
    # process which can push memory above 512MB.
    if settings.OPENAI_API_KEY:
        return _openai_embedding(text)

    model = _get_model()
    # encode -> numpy array; convert to python list for JSON/Qdrant client.
    return model.encode(text).tolist()

