def build_prompt(
    question: str,
    contexts: list,
    conversation_history: str | None = None,
):

    context_text = "\n\n".join(
        [
            c["text"]
            for c in contexts
        ]
    )

    history_block = """
Conversation so far:

{history}
""".format(history=conversation_history or "")

    return f"""
You are a customer support assistant.

Try to explain answer in 10-15 lines.

Use the conversation so far AND the supplied documentation.

If the answer cannot be found in the documentation, still try to answer using the conversation context.

If you truly cannot answer, reply exactly:

"I could not find this information in the uploaded documentation. (prompt service)"

Documentation:

{context_text}

{history_block}

Question:

{question}

Answer:
"""

