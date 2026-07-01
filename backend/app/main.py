import os
from pathlib import Path

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.auth import router as auth_router
from app.api.test import router as test_router
from app.api.me import router as me_router
from app.api.documents import router as document_router
from app.api.search import router as search_router
from app.api.dashboard import router as dashboard_router
from app.core.config import settings
from app.services.qdrant_service import create_collection
from app.api.chat import router as chat_router
from app.api.chat_session import router as chat_session_router
from app.websocket.chat_socket import router as websocket_router


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        origin.strip()
        for origin in settings.ALLOWED_ORIGINS.split(",")
        if origin.strip()
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(test_router)
app.include_router(me_router)
app.include_router(document_router)
app.include_router(search_router)
app.include_router(chat_router)
app.include_router(chat_session_router)
app.include_router(websocket_router)
app.include_router(dashboard_router)

@app.on_event("startup")
def startup():
    try:
        alembic_cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        alembic_cfg.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
        command.upgrade(alembic_cfg, "head")
        print("[startup] alembic upgrade completed")
    except Exception as exc:
        print("[startup] alembic upgrade failed:", repr(exc))

    try:
        create_collection()
        print("[startup] qdrant init completed")
    except Exception as exc:
        print("[startup] qdrant init failed:", repr(exc))


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)
