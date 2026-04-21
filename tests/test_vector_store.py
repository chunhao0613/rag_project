import pytest
from langchain_core.documents import Document

from services import vector_store as vs


def test_persist_dir_for_provider_mapping():
    assert vs._persist_dir_for_provider("google") == vs.CHROMA_GOOGLE_DIR
    assert vs._persist_dir_for_provider("cohere") == vs.CHROMA_COHERE_DIR
    assert vs._persist_dir_for_provider("together") == vs.CHROMA_TOGETHER_DIR
    assert vs._persist_dir_for_provider("huggingface") == vs.CHROMA_HF_DIR
    assert vs._persist_dir_for_provider("anything-else") == vs.CHROMA_LOCAL_DIR


def test_validate_vector_rejects_empty_vector():
    with pytest.raises(RuntimeError, match="empty embedding vector"):
        vs._validate_vector([], "mock-provider")


def test_embedding_for_unknown_provider_uses_local_hash():
    embedding = vs._embedding_for_provider("unknown", None)
    assert isinstance(embedding, vs.LocalHashEmbeddings)


def test_save_to_chroma_rejects_empty_chunks():
    with pytest.raises(ValueError, match="No chunks provided"):
        vs.save_to_chroma([], provider="google")


def test_save_to_chroma_falls_back_to_local_embeddings(monkeypatch, tmp_path):
    monkeypatch.setattr(vs, "CHROMA_GOOGLE_DIR", str(tmp_path / "google"))
    monkeypatch.setattr(vs, "CHROMA_COHERE_DIR", str(tmp_path / "cohere"))
    monkeypatch.setattr(vs, "CHROMA_TOGETHER_DIR", str(tmp_path / "together"))
    monkeypatch.setattr(vs, "CHROMA_HF_DIR", str(tmp_path / "hf"))
    monkeypatch.setattr(vs, "CHROMA_LOCAL_DIR", str(tmp_path / "local"))
    monkeypatch.setattr(vs, "EMBEDDING_BACKEND_DIR", str(tmp_path))

    def broken_embedding_provider(provider: str, model):
        raise RuntimeError("primary embedding unavailable")

    monkeypatch.setattr(vs, "_embedding_for_provider", broken_embedding_provider)

    captured = {}

    class DummyChroma:
        @classmethod
        def from_documents(cls, documents, embedding, persist_directory):
            captured["documents"] = documents
            captured["embedding"] = embedding
            captured["persist_directory"] = persist_directory
            return {"ok": True}

    monkeypatch.setattr(vs, "Chroma", DummyChroma)

    result = vs.save_to_chroma([Document(page_content="hello")], provider="google")

    assert result == {"ok": True}
    assert isinstance(captured["embedding"], vs.LocalHashEmbeddings)
    assert captured["persist_directory"] == str(tmp_path / "local")
