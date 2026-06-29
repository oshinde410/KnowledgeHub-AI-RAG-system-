from app.services.retrieval_service import retrieve_context
from app.services.prompt_service import build_prompt
from app.services.llm_service import generate_answer


def ask_rag(question: str):

    contexts = retrieve_context(None, question)

    if not contexts:
        return {
            "answer": "I could not find this information in the uploaded documentation. (rag service - not context)",
            "sources": []
        }

    if contexts[0]["score"] < 0.3:
        return {
            "answer": "I could not find this information in the uploaded documentation. (rag service - low score)",
            "sources": []
        }

    prompt = build_prompt(
        question,
        contexts
    )

    answer = generate_answer(prompt)

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

    return {
        "answer": answer
    }

    # return {
    #     "answer": answer_with_sources,
    #     "sources": contexts
    # }
