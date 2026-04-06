from typing import List
import os

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_google_genai import GoogleGenerativeAIEmbeddings

CHROMA_PERSIST_DIR = "./data/chroma_db"
EMBEDDING_MODEL = "models/embedding-001"


def _get_embeddings() -> GoogleGenerativeAIEmbeddings:
    """Create embeddings lazily so importing this module does not require credentials."""
    return GoogleGenerativeAIEmbeddings(model=EMBEDDING_MODEL)


def save_to_chroma(chunks: List[Document]) -> Chroma:
    """Save chunked documents to local Chroma and return the vector store."""
    if not chunks:
        raise ValueError("No chunks provided for vectorization.")

    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    try:
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=_get_embeddings(),
            persist_directory=CHROMA_PERSIST_DIR,
        )
        return vectorstore
    except Exception as exc:
        raise RuntimeError(f"Failed to write vector database: {exc}")


def get_vectorstore() -> Chroma:
    """Load existing Chroma vector store from local persistent path."""
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    return Chroma(
        persist_directory=CHROMA_PERSIST_DIR,
        embedding_function=_get_embeddings(),
    )
