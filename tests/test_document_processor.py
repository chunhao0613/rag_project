import pytest
from langchain_core.documents import Document

from core import document_processor as dp


class DummyLoader:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self):
        return [Document(page_content="first page"), Document(page_content="second page")]


class DummySplitter:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

    def split_documents(self, documents):
        assert len(documents) == 2
        return [Document(page_content="chunk-1"), Document(page_content="chunk-2")]


def test_process_pdf_success(monkeypatch):
    monkeypatch.setattr(dp, "PyPDFLoader", DummyLoader)
    monkeypatch.setattr(dp, "RecursiveCharacterTextSplitter", DummySplitter)

    chunks = dp.process_pdf("/tmp/sample.pdf")

    assert len(chunks) == 2
    assert chunks[0].page_content == "chunk-1"


def test_process_pdf_raises_when_no_documents(monkeypatch):
    class EmptyLoader:
        def __init__(self, file_path: str):
            self.file_path = file_path

        def load(self):
            return []

    monkeypatch.setattr(dp, "PyPDFLoader", EmptyLoader)

    with pytest.raises(ValueError, match="No extractable text"):
        dp.process_pdf("/tmp/empty.pdf")


def test_process_pdf_wraps_loader_error(monkeypatch):
    class BrokenLoader:
        def __init__(self, file_path: str):
            self.file_path = file_path

        def load(self):
            raise RuntimeError("broken pdf")

    monkeypatch.setattr(dp, "PyPDFLoader", BrokenLoader)

    with pytest.raises(ValueError, match="PDF load failed"):
        dp.process_pdf("/tmp/bad.pdf")
