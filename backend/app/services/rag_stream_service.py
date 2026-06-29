from app.services.retrieval_service import retrieve_context
from app.services.prompt_service import build_prompt
from app.services.llm_service import stream_answer


def stream_rag(question: str):

    contexts = retrieve_context(None, question)

    if not contexts:
        yield {
            "type": "done",
            "answer": "I could not find this information in the uploaded documentation. (rag stream service - not context)",
            "sources": []
        }
        return

    if contexts[0]["score"] < 0.1:
        yield {
            "type": "done",
            "answer": "I could not find this information in the uploaded documentation. (rag stream service - low score)",
            "sources": []
        }
        return

    prompt = build_prompt(
        question,
        contexts
    )

    full_answer = ""

    for token in stream_answer(prompt):

        full_answer += token

        yield {
            "type": "token",
            "content": token
        }

    # unique_doc_names = []
    # seen = set()
    # for c in contexts:
    #     name = c.get("document_name")
    #     if name and name not in seen:
    #         seen.add(name)
    #         unique_doc_names.append(name)

    # answer_with_sources = full_answer
    # if unique_doc_names:
    #     answer_with_sources = (
    #         full_answer
    #         + "\n\nSources:\n"
    #         + "\n".join([f"- {n}" for n in unique_doc_names])
    #     )

    yield {
        "type": "done",
        # "answer": answer_with_sources
        "answer": full_answer
        # "sources": contexts
    }
