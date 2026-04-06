from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI


def get_answer(vectorstore, query: str):
    """Run retrieval + generation and return a dict with 'result'."""
    if not query:
        return {"result": "Please provide a question."}

    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    docs = retriever.invoke(query)
    context = "\n\n".join(doc.page_content for doc in docs) if docs else ""

    if not context:
        return {"result": "Sorry, I cannot find an answer from the provided documents."}

    prompt = ChatPromptTemplate.from_template(
        """
You are a professional enterprise document assistant.
Answer the user question strictly based on the retrieved context below.
If the context does not contain the answer, say you cannot answer from the provided documents.

Retrieved context:
{context}

Question:
{question}
""".strip()
    )

    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    messages = prompt.format_messages(context=context, question=query)
    response = llm.invoke(messages)
    return {"result": response.content}
