import time
from typing import Generator


from sqlalchemy.orm import Session

from app.models.conversation import Conversation
from app.models.document import Document

from app.schemas.chat import ChatRequest
from app.services.conversation_service import (

    create_conversation,
    get_conversation,
    save_message,
)
from app.services.llm_service import generate_answer, stream_answer
from app.services.logging_service import log_ai_response, log_retrieval
from app.services.prompt_service import build_prompt
from app.services.conversation_service import list_messages
from app.services.retrieval_service import retrieve_context

FALLBACK_ANSWER = "I could not find this information in the uploaded documentation. (chat service)"


def _is_greeting(question: str) -> bool:
    q = (question or "").strip().lower()
    if not q:
        return False

    greeting_phrases = [
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
        "howdy",
    ]

    # Exact (or punctuation-terminated) greeting.
    for phrase in greeting_phrases:
        if q == phrase or q.rstrip("!?.") == phrase:
            return True

    # Greetings like "hi there" / "hello!".
    return any(q.startswith(phrase + " ") for phrase in greeting_phrases)


def _greeting_answer(question: str) -> str:
    # Keep it short and helpful.
    q = (question or "").strip().lower()
    if q.startswith("good morning"):
        salutation = "Good morning!"
    elif q.startswith("good afternoon"):
        salutation = "Good afternoon!"
    elif q.startswith("good evening"):
        salutation = "Good evening!"
    elif q.startswith("hey"):
        salutation = "Hey!"
    elif q.startswith("hello"):
        salutation = "Hello!"
    else:
        salutation = "Hi!"

    return (
        f"{salutation} I’m your support assistant. "
        "Ask me a question about your uploaded documentation, "
        "or attach a PDF in this chat to ground answers."
    )



def _conversation_for_request(db: Session, user_id: str, request: ChatRequest):
    if request.conversation_id:
        conversation = get_conversation(db, request.conversation_id, user_id=user_id)

        if conversation:
            return conversation

        # Client-provided conversation_id: preserve it so repeated questions stay in same backend conversation.
        print("Warning: conversation not found, creating with provided conversation_id")
        conversation = create_conversation(
            db=db,
            user_id=user_id,
            title=request.question[:50],
            conversation_id=request.conversation_id,
        )
        return conversation

    return create_conversation(
        db=db,
        user_id=user_id,
        title=request.question[:50],
    )



def ask_chat(db: Session, user_id: str, request: ChatRequest):
    conversation = _conversation_for_request(db, user_id, request)
    # Optionally restrict retrieval to a specific session scope.
    # If session_id is provided, ensure the request references only documents
    # that exist in this session.
    # Scope documents to this session.
    # Frontend may not send document_ids (it only sends session_id),
    # so we derive the scoped doc ids from Document.session_id.
    # Handle simple greeting messages without running retrieval/LLM.
    if _is_greeting(request.question):
        assistant_message = save_message(
            db=db,
            conversation_id=conversation.id,
            role="ASSISTANT",
            content=_greeting_answer(request.question),
            sources=[],
        )
        log_ai_response(db, "", assistant_message.content or "", 0, assistant_message.id)
        return {
            "conversation_id": conversation.id,
            "answer": assistant_message.content,
            "sources": [],
        }

    if request.session_id is not None:

        if request.document_ids:
            scoped_doc_rows = (
                db.query(Document)
                .filter(Document.id.in_(request.document_ids))
                .filter(Document.session_id == request.session_id)
                .all()
            )
            request.document_ids = [d.id for d in scoped_doc_rows]
        else:
            request.document_ids = [
                d.id for d in db.query(Document).filter(Document.session_id == request.session_id).all()
            ]

    user_message = save_message(
        db=db,
        conversation_id=conversation.id,
        role="USER",
        content=request.question
    )

    retrieval_started = time.perf_counter()
    contexts = retrieve_context(db, request.question, request.document_ids)
    print("=== RETRIEVAL DEBUG ===")
    print("question:", request.question)
    print("document_ids:", request.document_ids)
    print("contexts:", contexts)
    if contexts:
        print("top score:", contexts[0]["score"])
    print("=======================")
    retrieval_latency_ms = int((time.perf_counter() - retrieval_started) * 1000)
    log_retrieval(
        db=db,
        message_id=user_message.id,
        query_text=request.question,
        top_k=len(contexts),
        retrieval_latency_ms=retrieval_latency_ms
    )

    if not contexts or contexts[0]["score"] < 0.1:
        assistant_message = save_message(
            db=db,
            conversation_id=conversation.id,
            role="ASSISTANT",
            content=FALLBACK_ANSWER,
            sources=[]
        )
        log_ai_response(db, "", FALLBACK_ANSWER, 0, assistant_message.id)
        return {
            "conversation_id": conversation.id,
            "answer": FALLBACK_ANSWER,
            "sources": []
        }

    messages = list_messages(db, conversation.id, user_id)
    history = "".join(
        [
            f"{m.role}: {m.content}\n"
            for m in (messages or [])
            if m.content
        ][-20:]
    )

    prompt = build_prompt(request.question, contexts, conversation_history=history)
    generation_started = time.perf_counter()
    answer = generate_answer(prompt)
    generation_time_ms = int((time.perf_counter() - generation_started) * 1000)
    assistant_message = save_message(
        db=db,
        conversation_id=conversation.id,
        role="ASSISTANT",
        content=answer,
        sources=contexts
    )
    log_ai_response(
        db=db,
        message_id=assistant_message.id,
        prompt=prompt,
        answer=answer,
        generation_time_ms=generation_time_ms
    )

    unique_doc_names = []
    seen = set()
    for c in contexts:
        name = c.get("document_name")
        if name and name not in seen:
            seen.add(name)
            unique_doc_names.append(name)

    answer_with_sources = answer
    # if unique_doc_names:
    #     answer_with_sources = (
    #         answer
    #         + "\n\nSources:\n"
    #         + "\n".join([f"- {n}" for n in unique_doc_names])
    #     )

    assistant_message.content = answer_with_sources
    db.commit()

    return {
        "conversation_id": conversation.id,
        "answer": answer_with_sources,
        "sources": contexts
    }


def stream_chat(db: Session, user_id: str, request: ChatRequest) -> Generator[dict, None, None]:
    conversation = _conversation_for_request(db, user_id, request)
    user_message = save_message(db, conversation.id, "USER", request.question)

    # Handle simple greeting messages without running retrieval/LLM.
    if _is_greeting(request.question):
        assistant_message = save_message(
            db=db,
            conversation_id=conversation.id,
            role="ASSISTANT",
            content=_greeting_answer(request.question),
            sources=[],
        )
        log_ai_response(db, "", assistant_message.content or "", 0, assistant_message.id)
        yield {
            "type": "done",
            "conversation_id": conversation.id,
            "answer": assistant_message.content,
            "sources": [],
        }
        return

    retrieval_started = time.perf_counter()
    contexts = retrieve_context(db, request.question, request.document_ids)
    retrieval_latency_ms = int((time.perf_counter() - retrieval_started) * 1000)

    log_retrieval(db, request.question, len(contexts), retrieval_latency_ms, user_message.id)

    if not contexts or contexts[0]["score"] < 0.1:
        assistant_message = save_message(db, conversation.id, "ASSISTANT", FALLBACK_ANSWER, [])
        log_ai_response(db, "", FALLBACK_ANSWER, 0, assistant_message.id)
        yield {
            "type": "done",
            "conversation_id": conversation.id,
            "answer": FALLBACK_ANSWER,
            "sources": []
        }
        return

    messages = list_messages(db, conversation.id, user_id)
    history = "".join(
        [
            f"{m.role}: {m.content}\n"
            for m in (messages or [])
            if m.content
        ][-20:]
    )

    prompt = build_prompt(request.question, contexts, conversation_history=history)
    answer = ""
    generation_started = time.perf_counter()

    try:
        for token in stream_answer(prompt):
            answer += token
            yield {
                "type": "token",
                "content": token
            }
    except Exception as exc:
        print("[chat_service] stream_answer failed:", repr(exc))
        answer = FALLBACK_ANSWER
        yield {
            "type": "token",
            "content": ""
        }

    generation_time_ms = int((time.perf_counter() - generation_started) * 1000)
    assistant_message = save_message(db, conversation.id, "ASSISTANT", answer, contexts)
    log_ai_response(db, prompt, answer, generation_time_ms, assistant_message.id)

    # unique_doc_names = []
    # seen = set()
    # for c in contexts:
    #     name = c.get("document_name")
    #     if name and name not in seen:
    #         seen.add(name)
    #         unique_doc_names.append(name)

    # answer_with_sources = answer
    # if unique_doc_names:
    #     answer_with_sources = (
    #         answer
    #         + "\n\nSources:\n"
    #         + "\n".join([f"- {n}" for n in unique_doc_names])
    #     )

    yield {
        "type": "done",
        "conversation_id": conversation.id,
        "answer": answer,
        "sources": contexts
    }
