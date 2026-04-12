from typing import List, Optional, Any
import os
import math
import re
import json
import shutil
import requests

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.config import set_runtime_status

CHROMA_GOOGLE_DIR = "./data/chroma_db_google"
CHROMA_COHERE_DIR = "./data/chroma_db_cohere"
CHROMA_TOGETHER_DIR = "./data/chroma_db_together"
CHROMA_HF_DIR = "./data/chroma_db_hf"
CHROMA_LOCAL_DIR = "./data/chroma_db_local"
EMBEDDING_BACKEND_DIR = "./data"
EMBEDDING_REGISTRY_FILE = os.path.join(EMBEDDING_BACKEND_DIR, "_embedding_registry.json")
EMBEDDING_MODEL = os.getenv("GOOGLE_EMBEDDING_MODEL")
FALLBACK_EMBEDDING_MODELS = [
    "models/gemini-embedding-001",
    "models/text-embedding-004",
    "models/embedding-001",
]
_EMBEDDINGS_CLIENT: Optional[GoogleGenerativeAIEmbeddings] = None
_RESOLVED_EMBEDDING_MODEL: Optional[str] = None


def _backend_file(provider: str) -> str:
    safe_provider = provider.lower().strip()
    return os.path.join(EMBEDDING_BACKEND_DIR, f"_embedding_backend_{safe_provider}.txt")


def _registry_key(file_hash: str, provider: str, model: Optional[str]) -> str:
    model_name = (model or "default").strip() or "default"
    return f"{provider.lower().strip()}:{model_name}:{file_hash}"


def _load_embedding_registry() -> dict:
    if not os.path.exists(EMBEDDING_REGISTRY_FILE):
        return {}
    try:
        with open(EMBEDDING_REGISTRY_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _save_embedding_registry(registry: dict) -> None:
    os.makedirs(EMBEDDING_BACKEND_DIR, exist_ok=True)
    with open(EMBEDDING_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(registry, f, ensure_ascii=True, indent=2)


def is_document_embedded(file_hash: str, provider: str, model: Optional[str]) -> bool:
    """Check whether this file hash has been embedded for a provider+model."""
    if not file_hash:
        return False
    key = _registry_key(file_hash, provider, model)
    registry = _load_embedding_registry()
    return bool(registry.get(key, {}).get("embedded"))


def mark_document_embedded(
    file_hash: str,
    provider: str,
    model: Optional[str],
    file_name: Optional[str],
    chunk_count: int,
) -> None:
    if not file_hash:
        return
    key = _registry_key(file_hash, provider, model)
    registry = _load_embedding_registry()
    registry[key] = {
        "embedded": True,
        "file_hash": file_hash,
        "provider": provider.lower().strip(),
        "model": model or "default",
        "file_name": file_name or "",
        "chunk_count": int(chunk_count),
    }
    _save_embedding_registry(registry)


def clear_embedding_cache(provider: str, model: Optional[str] = None) -> dict:
    """Clear persisted embedding cache for a provider/model.

    Returns a summary dictionary with removed registry entries and whether
    vector directory was removed.
    """
    selected_provider = provider.lower().strip()
    model_name = (model or "").strip()

    registry = _load_embedding_registry()
    kept = {}
    removed = 0

    for key, value in registry.items():
        if not isinstance(value, dict):
            kept[key] = value
            continue
        key_provider = str(value.get("provider", "")).lower().strip()
        key_model = str(value.get("model", "")).strip()
        provider_match = key_provider == selected_provider
        model_match = (not model_name) or (key_model == model_name)
        if provider_match and model_match:
            removed += 1
            continue
        kept[key] = value

    if removed > 0:
        _save_embedding_registry(kept)

    persist_directory = _persist_dir_for_provider(selected_provider)
    vector_dir_removed = False
    if os.path.isdir(persist_directory):
        shutil.rmtree(persist_directory, ignore_errors=True)
        os.makedirs(persist_directory, exist_ok=True)
        vector_dir_removed = True

    backend_file = _backend_file(selected_provider)
    if os.path.exists(backend_file):
        try:
            os.remove(backend_file)
        except OSError:
            pass

    return {
        "provider": selected_provider,
        "model": model_name or "all-models",
        "removed_registry_entries": removed,
        "vector_dir_removed": vector_dir_removed,
    }


def _validate_vector(vector: List[float], provider: str) -> List[float]:
    if not isinstance(vector, list) or not vector:
        raise RuntimeError(f"{provider} returned an empty embedding vector.")
    cleaned = [float(x) for x in vector]
    if not cleaned:
        raise RuntimeError(f"{provider} returned an invalid embedding vector.")
    return cleaned


def _validate_vectors(vectors: List[List[float]], provider: str) -> List[List[float]]:
    if not isinstance(vectors, list) or not vectors:
        raise RuntimeError(f"{provider} returned empty embedding results.")
    return [_validate_vector(v, provider) for v in vectors]


class LocalHashEmbeddings(Embeddings):
    """Deterministic local embeddings as a no-quota fallback."""

    def __init__(self, dim: int = 384):
        self.dim = dim

    def _text_to_vector(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = [t for t in re.split(r"\s+", text.lower()) if t]

        # For CJK-heavy text or short text, add character-level signals.
        if len(tokens) < 3:
            tokens.extend(list(text))

        for token in tokens:
            idx = hash(token) % self.dim
            sign = 1.0 if (hash(token + "+") % 2 == 0) else -1.0
            vec[idx] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._text_to_vector(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._text_to_vector(text)


class HuggingFaceEmbeddings(Embeddings):
    def __init__(self, model: str):
        self.model = model
        self.api_key = os.getenv("HF_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Hugging Face token is missing. Set HF_API_KEY.")

    def _to_vector(self, payload: Any) -> List[float]:
        if isinstance(payload, list) and payload and isinstance(payload[0], (int, float)):
            return [float(x) for x in payload]
        if isinstance(payload, list) and payload and isinstance(payload[0], list):
            dim = len(payload[0])
            if dim == 0:
                return []
            sums = [0.0] * dim
            count = 0
            for row in payload:
                if not isinstance(row, list) or len(row) != dim:
                    continue
                for i, val in enumerate(row):
                    sums[i] += float(val)
                count += 1
            if count == 0:
                return []
            return [x / count for x in sums]
        return []

    def _request_embedding(self, text: str) -> List[float]:
        url = f"https://api-inference.huggingface.co/pipeline/feature-extraction/{self.model}"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        response = requests.post(
            url,
            headers=headers,
            json={"inputs": text, "options": {"wait_for_model": True}},
            timeout=90,
        )
        set_runtime_status(
            "embedding",
            "huggingface",
            {
                "remaining_requests": response.headers.get("x-ratelimit-remaining", "unknown"),
                "status": "ok" if response.ok else "error",
            },
        )
        response.raise_for_status()
        return _validate_vector(self._to_vector(response.json()), "huggingface")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._request_embedding(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._request_embedding(text)


class CohereEmbeddings(Embeddings):
    def __init__(self, model: str):
        self.model = model
        self.api_key = os.getenv("COHERE_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Cohere API key is missing. Set COHERE_API_KEY.")

    def _request_embeddings(self, texts: List[str], input_type: str) -> List[List[float]]:
        url = "https://api.cohere.com/v1/embed"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "texts": texts,
            "model": self.model,
            "input_type": input_type,
            "embedding_types": ["float"],
        }
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        set_runtime_status(
            "embedding",
            "cohere",
            {
                "status": "ok" if response.ok else "error",
            },
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data.get("embeddings")
        # Cohere response formats vary by API/version/model:
        # 1) embeddings: [[...], [...]]
        # 2) embeddings: {"float": [[...], [...]]}
        # 3) embeddings_by_type: {"float": [[...], [...]]}
        if isinstance(embeddings, list):
            vectors = [[float(x) for x in row] for row in embeddings]
            return _validate_vectors(vectors, "cohere")
        if isinstance(embeddings, dict):
            float_embeddings = embeddings.get("float")
            if isinstance(float_embeddings, list):
                vectors = [[float(x) for x in row] for row in float_embeddings]
                return _validate_vectors(vectors, "cohere")
        embeddings_by_type = data.get("embeddings_by_type", {})
        if isinstance(embeddings_by_type, dict):
            float_embeddings = embeddings_by_type.get("float")
            if isinstance(float_embeddings, list):
                vectors = [[float(x) for x in row] for row in float_embeddings]
                return _validate_vectors(vectors, "cohere")
        error_hint = data.get("message") if isinstance(data, dict) else None
        raise RuntimeError(f"cohere response did not include embeddings. {error_hint or ''}".strip())

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._request_embeddings(texts, input_type="search_document")

    def embed_query(self, text: str) -> List[float]:
        vectors = self._request_embeddings([text], input_type="search_query")
        return vectors[0] if vectors else []


class TogetherAIEmbeddings(Embeddings):
    def __init__(self, model: str):
        self.model = model
        self.api_key = os.getenv("TOGETHER_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("Together AI API key is missing. Set TOGETHER_API_KEY.")

    def _request_embeddings(self, texts: List[str]) -> List[List[float]]:
        url = "https://api.together.xyz/v1/embeddings"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "input": texts,
        }
        response = requests.post(url, headers=headers, json=payload, timeout=90)
        set_runtime_status(
            "embedding",
            "together",
            {
                "status": "ok" if response.ok else "error",
            },
        )
        response.raise_for_status()
        data = response.json()
        rows = data.get("data", [])
        if isinstance(rows, list):
            vectors = [item.get("embedding", []) for item in rows if isinstance(item, dict)]
            return _validate_vectors(vectors, "together")
        raise RuntimeError("together response did not include embeddings.")

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._request_embeddings(texts)

    def embed_query(self, text: str) -> List[float]:
        vectors = self._request_embeddings([text])
        return vectors[0] if vectors else []


def _is_quota_error(error_msg: str) -> bool:
    msg = error_msg.lower()
    return (
        "429" in msg
        or "quota" in msg
        or "rate limit" in msg
        or "spending cap" in msg
    )


def _save_backend_for_provider(provider: str, backend_value: str) -> None:
    os.makedirs(EMBEDDING_BACKEND_DIR, exist_ok=True)
    with open(_backend_file(provider), "w", encoding="utf-8") as f:
        f.write(backend_value)


def _read_embedding_backend(provider: str) -> Optional[str]:
    file_path = _backend_file(provider)
    if not os.path.exists(file_path):
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        value = f.read().strip()
    return value or None


def _get_google_embeddings(preferred_model: Optional[str] = None) -> GoogleGenerativeAIEmbeddings:
    """Create embeddings lazily and resolve a model compatible with the current API key."""
    global _EMBEDDINGS_CLIENT, _RESOLVED_EMBEDDING_MODEL

    if _EMBEDDINGS_CLIENT is not None and (
        preferred_model is None or preferred_model == _RESOLVED_EMBEDDING_MODEL
    ):
        return _EMBEDDINGS_CLIENT

    candidate_models: List[str] = []
    if preferred_model:
        candidate_models.append(preferred_model)
    if EMBEDDING_MODEL and EMBEDDING_MODEL not in candidate_models:
        candidate_models.append(EMBEDDING_MODEL)
    for fallback_model in FALLBACK_EMBEDDING_MODELS:
        if fallback_model not in candidate_models:
            candidate_models.append(fallback_model)

    errors: List[str] = []

    for model_name in candidate_models:
        if not model_name:
            continue

        try:
            embeddings = GoogleGenerativeAIEmbeddings(model=model_name)
            # Probe once to confirm this model is available for this key/project.
            embeddings.embed_query("model availability check")
            _EMBEDDINGS_CLIENT = embeddings
            _RESOLVED_EMBEDDING_MODEL = model_name
            return embeddings
        except Exception as exc:
            errors.append(f"{model_name}: {exc}")

    guidance = (
        "Unable to find a supported embedding model for this API key. "
        "Set GOOGLE_EMBEDDING_MODEL to a model available in your account, "
        "for example models/gemini-embedding-001."
    )
    error_details = " | ".join(errors) if errors else "No candidate model was tested."
    raise RuntimeError(f"{guidance} Details: {error_details}")


def _persist_dir_for_provider(provider: str) -> str:
    p = provider.lower().strip()
    if p == "google":
        return CHROMA_GOOGLE_DIR
    if p == "cohere":
        return CHROMA_COHERE_DIR
    if p == "together":
        return CHROMA_TOGETHER_DIR
    if p == "huggingface":
        return CHROMA_HF_DIR
    return CHROMA_LOCAL_DIR


def _embedding_for_provider(provider: str, model: Optional[str]) -> Embeddings:
    p = provider.lower().strip()
    if p == "google":
        return _get_google_embeddings(preferred_model=model)
    if p == "cohere":
        cohere_model = model or os.getenv("COHERE_EMBEDDING_MODEL", "embed-english-v3.0")
        return CohereEmbeddings(model=cohere_model)
    if p == "together":
        together_model = model or os.getenv("TOGETHER_EMBEDDING_MODEL", "BAAI/bge-small-en-v1.5")
        return TogetherAIEmbeddings(model=together_model)
    if p == "huggingface":
        hf_model = model or os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        return HuggingFaceEmbeddings(model=hf_model)
    return LocalHashEmbeddings()


def save_to_chroma(
    chunks: List[Document],
    provider: str = "google",
    model: Optional[str] = None,
    file_hash: Optional[str] = None,
    file_name: Optional[str] = None,
) -> Chroma:
    """Save chunked documents to local Chroma and return the vector store."""
    if not chunks:
        raise ValueError("No chunks provided for vectorization.")

    os.makedirs(CHROMA_GOOGLE_DIR, exist_ok=True)
    os.makedirs(CHROMA_COHERE_DIR, exist_ok=True)
    os.makedirs(CHROMA_TOGETHER_DIR, exist_ok=True)
    os.makedirs(CHROMA_HF_DIR, exist_ok=True)
    os.makedirs(CHROMA_LOCAL_DIR, exist_ok=True)

    selected_provider = provider.lower().strip()
    persist_directory = _persist_dir_for_provider(selected_provider)

    try:
        embeddings = _embedding_for_provider(selected_provider, model)
        vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=embeddings,
            persist_directory=persist_directory,
        )
        model_name = model or _RESOLVED_EMBEDDING_MODEL or EMBEDDING_MODEL or "default"
        _save_backend_for_provider(selected_provider, f"{selected_provider}:{model_name}")
        set_runtime_status("embedding", selected_provider, {"status": "ok", "backend": selected_provider})
        if file_hash:
            mark_document_embedded(
                file_hash=file_hash,
                provider=selected_provider,
                model=model_name,
                file_name=file_name,
                chunk_count=len(chunks),
            )
        return vectorstore
    except Exception as exc:
        error_msg = str(exc)
        try:
            local_embeddings = LocalHashEmbeddings()
            vectorstore = Chroma.from_documents(
                documents=chunks,
                embedding=local_embeddings,
                persist_directory=CHROMA_LOCAL_DIR,
            )
            _save_backend_for_provider(selected_provider, "local-hash-v1")
            set_runtime_status(
                "embedding",
                selected_provider,
                {"status": "degraded", "backend": "local", "reason": str(exc)},
            )
            return vectorstore
        except Exception as local_exc:
            raise RuntimeError(
                f"Failed to write vector database with provider '{selected_provider}': {error_msg}. "
                f"Local fallback also failed: {local_exc}"
            ) from local_exc


def get_vectorstore(provider: str = "google", model: Optional[str] = None) -> Chroma:
    """Load existing Chroma vector store from local persistent path."""
    os.makedirs(CHROMA_GOOGLE_DIR, exist_ok=True)
    os.makedirs(CHROMA_COHERE_DIR, exist_ok=True)
    os.makedirs(CHROMA_TOGETHER_DIR, exist_ok=True)
    os.makedirs(CHROMA_HF_DIR, exist_ok=True)
    os.makedirs(CHROMA_LOCAL_DIR, exist_ok=True)

    selected_provider = provider.lower().strip()
    backend = _read_embedding_backend(selected_provider)
    try:
        if backend == "local-hash-v1":
            embedding_function: Embeddings = LocalHashEmbeddings()
            persist_directory = CHROMA_LOCAL_DIR
        else:
            embedding_function = _embedding_for_provider(selected_provider, model)
            persist_directory = _persist_dir_for_provider(selected_provider)
    except Exception as exc:
        # Retrieval must remain available; degrade to local embeddings when provider embedding is unavailable.
        embedding_function = LocalHashEmbeddings()
        persist_directory = CHROMA_LOCAL_DIR
        _save_backend_for_provider(selected_provider, "local-hash-v1")
        set_runtime_status(
            "embedding",
            selected_provider,
            {
                "status": "degraded",
                "backend": "local",
                "reason": str(exc),
            },
        )

    return Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding_function,
    )
