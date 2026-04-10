from typing import Any, Dict, List
import os

import requests

EMBEDDING_PROVIDERS = ["google", "azure", "huggingface", "local"]
LLM_PROVIDERS = ["google", "azure", "huggingface"]

DEFAULT_EMBEDDING_MODELS: Dict[str, List[str]] = {
	"google": [
		"models/gemini-embedding-001",
		"models/text-embedding-004",
	],
	"azure": [
		"text-embedding-3-small",
	],
	"huggingface": [
		"sentence-transformers/all-MiniLM-L6-v2",
		"BAAI/bge-small-en-v1.5",
	],
	"local": ["local-hash-v1"],
}

DEFAULT_LLM_MODELS: Dict[str, List[str]] = {
	"google": [
		"gemini-2.0-flash-lite",
		"gemini-2.0-flash",
		"gemini-flash-latest",
		"gemini-2.5-flash",
	],
	"azure": [
		"gpt-4o-mini",
	],
	"huggingface": [
		"mistralai/Mistral-7B-Instruct-v0.3",
		"meta-llama/Llama-3.1-8B-Instruct",
	],
}

_RUNTIME_STATUS: Dict[str, Dict[str, Any]] = {
	"embedding": {},
	"llm": {},
}


def set_runtime_status(scope: str, provider: str, data: Dict[str, Any]) -> None:
	bucket = _RUNTIME_STATUS.setdefault(scope, {})
	bucket[provider] = data


def get_runtime_status(scope: str, provider: str) -> Dict[str, Any]:
	return _RUNTIME_STATUS.get(scope, {}).get(provider, {})


def _google_models_for_method(api_key: str, method_name: str) -> List[str]:
	url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
	response = requests.get(url, timeout=20)
	response.raise_for_status()
	payload = response.json()
	models: List[str] = []
	for item in payload.get("models", []):
		methods = item.get("supportedGenerationMethods", [])
		name = item.get("name", "")
		if method_name in methods and name.startswith("models/"):
			models.append(name.replace("models/", "", 1))
	return models


def _csv_env_list(env_name: str) -> List[str]:
	value = os.getenv(env_name, "").strip()
	if not value:
		return []
	return [x.strip() for x in value.split(",") if x.strip()]


def get_available_models(provider: str, kind: str) -> List[str]:
	provider = provider.lower().strip()
	kind = kind.lower().strip()

	if provider == "google":
		api_key = os.getenv("GOOGLE_API_KEY", "").strip()
		if not api_key:
			return DEFAULT_LLM_MODELS["google"] if kind == "llm" else DEFAULT_EMBEDDING_MODELS["google"]
		try:
			method = "generateContent" if kind == "llm" else "embedContent"
			dynamic_models = _google_models_for_method(api_key, method)
			if kind == "embedding":
				dynamic_models = [f"models/{m}" for m in dynamic_models if not m.startswith("models/")]
			return dynamic_models or (
				DEFAULT_LLM_MODELS["google"] if kind == "llm" else DEFAULT_EMBEDDING_MODELS["google"]
			)
		except Exception:
			return DEFAULT_LLM_MODELS["google"] if kind == "llm" else DEFAULT_EMBEDDING_MODELS["google"]

	if provider == "azure":
		if kind == "llm":
			return _csv_env_list("AZURE_OPENAI_CHAT_DEPLOYMENTS") or DEFAULT_LLM_MODELS["azure"]
		return _csv_env_list("AZURE_OPENAI_EMBEDDING_DEPLOYMENTS") or DEFAULT_EMBEDDING_MODELS["azure"]

	if provider == "huggingface":
		if kind == "llm":
			return _csv_env_list("HF_LLM_MODELS") or DEFAULT_LLM_MODELS["huggingface"]
		return _csv_env_list("HF_EMBEDDING_MODELS") or DEFAULT_EMBEDDING_MODELS["huggingface"]

	if kind == "llm":
		return []
	return DEFAULT_EMBEDDING_MODELS.get("local", ["local-hash-v1"])
