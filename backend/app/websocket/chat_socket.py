from fastapi import APIRouter
from fastapi import Query
from fastapi import WebSocket
from fastapi import WebSocketDisconnect
from jose import JWTError
from jose import jwt
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.user import User
from app.websocket.manager import manager
from app.schemas.chat import ChatRequest
from app.services.chat_service import stream_chat

router = APIRouter()

@router.websocket("/ws/chat")
async def websocket_chat(
    websocket: WebSocket,
    token: str | None = Query(default=None)
):
    db = SessionLocal()

    try:
        if not token:
            await websocket.close(code=1008)
            return

        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
        user_id = payload.get("sub")
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            await websocket.close(code=1008)
            return
    except JWTError:
        await websocket.close(code=1008)
        db.close()
        return

    await manager.connect(websocket)

    try:

        while True:

            data = await websocket.receive_json()

            question = data.get("question")
            conversation_id = data.get("conversation_id")

            if not question:

                await manager.send_json(
                    websocket,
                    {
                        "type": "error",
                        "message": "Question is required."
                    }
                )

                continue

            request = ChatRequest(
                question=question,
                conversation_id=conversation_id,
                document_ids=data.get("document_ids") or []
            )

            try:
                for event in stream_chat(db, user.id, request):
                    await manager.send_json(websocket, event)
            except Exception as exc:
                print("[websocket] stream failed:", repr(exc))
                await manager.send_json(
                    websocket,
                    {
                        "type": "done",
                        "conversation_id": conversation_id,
                        "answer": "The service is currently unavailable. Please try again shortly.",
                        "sources": []
                    }
                )

    except WebSocketDisconnect:

        manager.disconnect(websocket)
    finally:
        db.close()
