from typing import List, Optional
import re
import os

import requests

from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from core.config import set_runtime_status

CHAT_MODEL = os.getenv("GOOGLE_CHAT_MODEL")
FALLBACK_CHAT_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash",
    "gemini-flash-latest",
    "gemini-2.5-flash",
    "gemini-pro-latest",
]
_LLM_CLIENT: Optional[ChatGoogleGenerativeAI] = None
_RESOLVED_CHAT_MODEL: Optional[str] = None


def _get_llm() -> ChatGoogleGenerativeAI:
    """Create chat model lazily from the preferred model (without probing requests)."""
    global _LLM_CLIENT, _RESOLVED_CHAT_MODEL

    if _LLM_CLIENT is not None:
        return _LLM_CLIENT

    model_name = CHAT_MODEL or FALLBACK_CHAT_MODELS[0]
    _LLM_CLIENT = ChatGoogleGenerativeAI(model=model_name, max_retries=0)
    _RESOLVED_CHAT_MODEL = model_name
    return _LLM_CLIENT


def _azure_chat(prompt_text: str, deployment: str) -> str:
    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    api_key = os.getenv("AZURE_OPENAI_API_KEY") or os.getenv("AZURE_OPENAI_KEY", "")
    api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
    if not endpoint or not api_key:
        raise RuntimeError("Azure OpenAI credentials are missing. Set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY.")

    url = f"{endpoint}/openai/deployments/{deployment}/chat/completions?api-version={api_version}"
    headers = {
        "api-key": api_key,
        "Content-Type": "application/json",
    }
    payload = {
        "messages": [
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.2,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=90)
    set_runtime_status(
        "llm",
        "azure",
        {
            "remaining_requests": response.headers.get("x-ratelimit-remaining-requests", "unknown"),
            "remaining_tokens": response.headers.get("x-ratelimit-remaining-tokens", "unknown"),
            "status": "ok" if response.ok else "error",
        },
    )
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")


def _hf_chat(prompt_text: str, model: str) -> str:
    api_key = os.getenv("HF_API_KEY", "")
    if not api_key:
        raise RuntimeError("Hugging Face token is missing. Set HF_API_KEY.")
    url = f"https://api-inference.huggingface.co/models/{model}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "inputs": prompt_text,
        "parameters": {
            "max_new_tokens": 300,
            "temperature": 0.2,
            "return_full_text": False,
        },
        "options": {"wait_for_model": True},
    }
    response = requests.post(url, headers=headers, json=payload, timeout=120)
    set_runtime_status(
        "llm",
        "huggingface",
        {
            "remaining_requests": response.headers.get("x-ratelimit-remaining", "unknown"),
            "status": "ok" if response.ok else "error",
        },
    )
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list) and data:
        return data[0].get("generated_text", "")
    if isinstance(data, dict):
        return data.get("generated_text", "")
    return ""


def _extract_retry_seconds(error_text: str) -> Optional[int]:
    retry_patterns = [
        r"retry in\s+([0-9]+(?:\.[0-9]+)?)s",
        r"retry_delay\s*\{\s*seconds:\s*([0-9]+)",
    ]
    for pattern in retry_patterns:
        match = re.search(pattern, error_text, flags=re.IGNORECASE)
        if match:
            try:
                return max(1, int(float(match.group(1))))
            except (TypeError, ValueError):
                return None
    return None


def _invoke_google_with_model_fallback(messages, preferred_model: Optional[str] = None):
    """Invoke chat model with fallback for model-availability failures."""
    global _LLM_CLIENT, _RESOLVED_CHAT_MODEL

    # Try the cached/preferred model first.
    primary_model = preferred_model or _RESOLVED_CHAT_MODEL or CHAT_MODEL or FALLBACK_CHAT_MODELS[0]
    candidate_models: List[str] = []
    for name in [primary_model] + FALLBACK_CHAT_MODELS:
        if name and name not in candidate_models:
            candidate_models.append(name)

    errors: List[str] = []

    for model_name in candidate_models:
        try:
            llm = ChatGoogleGenerativeAI(model=model_name, max_retries=0)
            response = llm.invoke(messages)
            _LLM_CLIENT = llm
            _RESOLVED_CHAT_MODEL = model_name
            return response
        except Exception as exc:
            err = str(exc)
            err_lower = err.lower()

            if "429" in err_lower or "quota" in err_lower or "rate limit" in err_lower:
                retry_seconds = _extract_retry_seconds(err)
                wait_hint = (
                    f" Please retry after about {retry_seconds} seconds."
                    if retry_seconds
                    else " Please retry after a short wait."
                )
                raise RuntimeError(
                    "Gemini API quota exceeded." + wait_hint
                ) from exc

            errors.append(f"{model_name}: {err}")

    guidance = (
        "No supported chat model is available for this API key. "
        "Set GOOGLE_CHAT_MODEL to a model that supports generateContent, "
        "for example gemini-2.0-flash-lite."
    )
    detail = " | ".join(errors) if errors else "No candidate model was tested."
    raise RuntimeError(f"{guidance} Details: {detail}")


def _run_llm(provider: str, model: str, prompt_text: str, messages):
    p = provider.lower().strip()
    if p == "google":
        response = _invoke_google_with_model_fallback(messages, preferred_model=model)
        set_runtime_status("llm", "google", {"status": "ok", "model": model})
        return response.content
    if p == "azure":
        return _azure_chat(prompt_text, deployment=model)
    if p == "huggingface":
        return _hf_chat(prompt_text, model=model)
    raise RuntimeError(f"Unsupported llm provider: {provider}")


def _build_extractive_fallback_answer(query: str, docs) -> str:
    snippets: List[str] = []
    for i, doc in enumerate(docs[:3], start=1):
        text = (doc.page_content or "").strip().replace("\n", " ")
        if not text:
            continue
        snippets.append(f"{i}. {text[:260]}")

    if not snippets:
        return "目前無法使用雲端模型，且檢索不到可用片段。"

    return (
        "目前因配額限制改用擷取式回答（非生成式）。\n\n"
        f"你的問題：{query}\n"
        "可參考文件片段：\n"
        + "\n".join(snippets)
    )


def get_answer(vectorstore, query: str, provider: str = "google", model: Optional[str] = None):
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

    try:
        selected_provider = provider.lower().strip()
        if selected_provider == "google":
            _get_llm()
            selected_model = model or (_RESOLVED_CHAT_MODEL or CHAT_MODEL or FALLBACK_CHAT_MODELS[0])
        elif selected_provider == "azure":
            azure_models = [x.strip() for x in os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENTS", "gpt-4o-mini").split(",") if x.strip()]
            selected_model = model or azure_models[0]
        elif selected_provider == "huggingface":
            hf_models = [x.strip() for x in os.getenv("HF_LLM_MODELS", "mistralai/Mistral-7B-Instruct-v0.3").split(",") if x.strip()]
            selected_model = model or hf_models[0]
        else:
            raise RuntimeError(f"Unsupported llm provider: {provider}")

        messages = prompt.format_messages(context=context, question=query)
        prompt_text = messages[-1].content if messages else query
        answer_text = _run_llm(selected_provider, selected_model, prompt_text, messages)
        return {"result": answer_text}
    except Exception as exc:
        err = str(exc).lower()
        if "429" in err or "quota" in err or "spending cap" in err or "rate limit" in err:
            retry_seconds = _extract_retry_seconds(str(exc))
            set_runtime_status(
                "llm",
                provider.lower().strip(),
                {
                    "status": "quota_exceeded",
                    "retry_after_seconds": retry_seconds if retry_seconds else "unknown",
                    "reason": str(exc),
                },
            )
            return {"result": _build_extractive_fallback_answer(query, docs)}
        set_runtime_status(
            "llm",
            provider.lower().strip(),
            {
                "status": "error",
                "reason": str(exc),
            },
        )
        return {
            "result": (
                "The assistant model is currently unavailable for this API key. "
                "Please set GOOGLE_CHAT_MODEL to a supported model and retry. "
                f"Error: {exc}"
            )
        }
