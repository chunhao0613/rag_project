from typing import List

from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def process_pdf(file_path: str) -> List[Document]:
    """Load a PDF and split it into chunks suitable for indexing."""
    try:
        loader = PyPDFLoader(file_path)
        documents = loader.load()
    except Exception as exc:
        raise ValueError(f"PDF load failed: {exc}")

    if not documents:
        raise ValueError("No extractable text was found in this PDF.")

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", "。", "，", " ", ""],
    )

    return text_splitter.split_documents(documents)


if __name__ == "__main__":
    pass
