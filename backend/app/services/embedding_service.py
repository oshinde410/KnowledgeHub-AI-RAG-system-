from __future__ import annotations

from typing import Any

_model: Any | None = None


def _get_model():
    """Lazy-load the SentenceTransformer model.

    Render free-tier RAM is limited; importing this module should stay light.
    The first embedding call loads the model once per process.
    """
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        # Keep the same model for compatibility.
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def create_embedding(text: str):
    model = _get_model()
    # encode -> numpy array; convert to python list for JSON/Qdrant client.
    return model.encode(text).tolist()

