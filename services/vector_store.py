from typing import List, Optional, Any
import os
import math
import re
import requests

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from core.config import set_runtime_status

CHROMA_GOOGLE_DIR = "./data/chroma_db_google"
CHROMA_AZURE_DIR = "./data/chroma_db_azure"
CHROMA_HF_DIR = "./data/chroma_db_hf"
CHROMA_LOCAL_DIR = "./data/chroma_db_local"
EMBEDDING_BACKEND_DIR = "./data"
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


class AzureOpenAIEmbeddings(Embeddings):
    def __init__(self, deployment: str):
        self.deployment = deployment
        self.endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
        self.api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY", "")
        self.api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
        if not self.endpoint or not self.api_key:
            raise RuntimeError("Azure OpenAI credentials are missing. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.")

    def _request_embeddings(self, texts: List[str]) -> List[List[float]]:
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment}/embeddings"
            f"?api-version={self.api_version}"
        )
        headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        response = requests.post(url, headers=headers, json={"input": texts}, timeout=60)
        set_runtime_status(
            "embedding",
            "azure",
            {
                "remaining_requests": response.headers.get("x-ratelimit-remaining-requests", "unknown"),
                "remaining_tokens": response.headers.get("x-ratelimit-remaining-tokens", "unknown"),
                "status": "ok" if response.ok else "error",
            },
        )
        response.raise_for_status()
        data = response.json().get("data", [])
        data = sorted(data, key=lambda x: x.get("index", 0))
        return [item.get("embedding", []) for item in data]

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return self._request_embeddings(texts)

    def embed_query(self, text: str) -> List[float]:
        vectors = self._request_embeddings([text])
        return vectors[0] if vectors else []


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
        return self._to_vector(response.json())

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        return [self._request_embedding(text) for text in texts]

    def embed_query(self, text: str) -> List[float]:
        return self._request_embedding(text)


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
    if p == "azure":
        return CHROMA_AZURE_DIR
    if p == "huggingface":
        return CHROMA_HF_DIR
    return CHROMA_LOCAL_DIR


def _embedding_for_provider(provider: str, model: Optional[str]) -> Embeddings:
    p = provider.lower().strip()
    if p == "google":
        return _get_google_embeddings(preferred_model=model)
    if p == "azure":
        deployment = model or os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT", "text-embedding-3-small")
        return AzureOpenAIEmbeddings(deployment=deployment)
    if p == "huggingface":
        hf_model = model or os.getenv("HF_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
        return HuggingFaceEmbeddings(model=hf_model)
    return LocalHashEmbeddings()


def save_to_chroma(chunks: List[Document], provider: str = "google", model: Optional[str] = None) -> Chroma:
    """Save chunked documents to local Chroma and return the vector store."""
    if not chunks:
        raise ValueError("No chunks provided for vectorization.")

    os.makedirs(CHROMA_GOOGLE_DIR, exist_ok=True)
    os.makedirs(CHROMA_AZURE_DIR, exist_ok=True)
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
        return vectorstore
    except Exception as exc:
        error_msg = str(exc)
        if _is_quota_error(error_msg) or "not found" in error_msg.lower() or "unsupported" in error_msg.lower() or "401" in error_msg.lower():
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
        raise RuntimeError(f"Failed to write vector database: {exc}") from exc


def get_vectorstore(provider: str = "google", model: Optional[str] = None) -> Chroma:
    """Load existing Chroma vector store from local persistent path."""
    os.makedirs(CHROMA_GOOGLE_DIR, exist_ok=True)
    os.makedirs(CHROMA_AZURE_DIR, exist_ok=True)
    os.makedirs(CHROMA_HF_DIR, exist_ok=True)
    os.makedirs(CHROMA_LOCAL_DIR, exist_ok=True)

    selected_provider = provider.lower().strip()
    backend = _read_embedding_backend(selected_provider)
    if backend == "local-hash-v1":
        embedding_function: Embeddings = LocalHashEmbeddings()
        persist_directory = CHROMA_LOCAL_DIR
    else:
        embedding_function = _embedding_for_provider(selected_provider, model)
        persist_directory = _persist_dir_for_provider(selected_provider)

    return Chroma(
        persist_directory=persist_directory,
        embedding_function=embedding_function,
    )
