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
            "model": model,
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


def _groq_chat(prompt_text: str, model: str) -> str:
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        raise RuntimeError("Groq API key is missing. Set GROQ_API_KEY.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.2,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=90)
    status_payload = {
        "status": "ok" if response.ok else "error",
        "model": model,
    }
    if response.ok:
        try:
            usage = response.json().get("usage", {})
            if usage:
                status_payload["prompt_tokens"] = usage.get("prompt_tokens", "unknown")
                status_payload["completion_tokens"] = usage.get("completion_tokens", "unknown")
        except Exception:
            pass
    set_runtime_status("llm", "groq", status_payload)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")


def _github_models_chat(prompt_text: str, model: str) -> str:
    api_key = os.getenv("GITHUB_MODELS_TOKEN", "")
    if not api_key:
        raise RuntimeError("GitHub Models token is missing. Set GITHUB_MODELS_TOKEN.")

    url = "https://models.inference.ai.azure.com/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": prompt_text},
        ],
        "temperature": 0.2,
    }
    response = requests.post(url, headers=headers, json=payload, timeout=90)
    status_payload = {
        "status": "ok" if response.ok else "error",
        "model": model,
        "remaining_requests": response.headers.get("x-ratelimit-remaining-requests", "unknown"),
        "remaining_tokens": response.headers.get("x-ratelimit-remaining-tokens", "unknown"),
    }
    if not response.ok:
        try:
            err_json = response.json()
            message = (
                err_json.get("error", {}).get("message")
                if isinstance(err_json, dict)
                else None
            )
            if message:
                status_payload["error_message"] = message
        except Exception:
            pass
    set_runtime_status("llm", "github-models", status_payload)
    response.raise_for_status()
    data = response.json()
    choices = data.get("choices", [])
    if not choices:
        return ""
    return choices[0].get("message", {}).get("content", "")


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
    if p == "huggingface":
        return _hf_chat(prompt_text, model=model)
    if p == "groq":
        return _groq_chat(prompt_text, model=model)
    if p == "github-models":
        return _github_models_chat(prompt_text, model=model)
    raise RuntimeError(f"Unsupported llm provider: {provider}")


def _provider_retry_hint(provider: str) -> str:
    p = provider.lower().strip()
    if p == "google":
        return "請確認 GOOGLE_CHAT_MODEL 可用，或改用 github-models / groq。"
    if p == "github-models":
        return "請改用 gpt-4o-mini，並確認 GITHUB_MODELS_TOKEN 有該模型權限。"
    if p == "huggingface":
        return "請確認 HF_API_KEY 有效，並優先選擇公開可用模型。"
    if p == "groq":
        return "請確認 GROQ_API_KEY 有效且模型仍在可用清單。"
    return "請檢查模型名稱與 API Key 權限。"


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

    docs = []
    try:
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
        docs = retriever.invoke(query)
    except Exception as exc:
        set_runtime_status(
            "embedding",
            "retrieval",
            {
                "status": "error",
                "reason": str(exc),
            },
        )
        return {
            "result": (
                "文件檢索暫時失敗，可能是向量維度與目前 Embedding Provider 不一致。"
                "請重新上傳 PDF 以用目前的 Embedding Provider 重建索引後再試。"
                f" Error: {exc}"
            )
        }

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
        elif selected_provider == "huggingface":
            hf_models = [
                x.strip()
                for x in os.getenv(
                    "HF_LLM_MODELS",
                    "mistralai/Mistral-7B-Instruct-v0.3,microsoft/phi-3.5-mini-instruct,TinyLlama/TinyLlama-1.1B-Chat-v1.0",
                ).split(",")
                if x.strip()
            ]
            selected_model = model or hf_models[0]
        elif selected_provider == "groq":
            groq_models = [
                x.strip()
                for x in os.getenv(
                    "GROQ_LLM_MODELS",
                    "llama-3.1-8b-instant,llama-3.3-70b-versatile,gemma2-9b-it",
                ).split(",")
                if x.strip()
            ]
            selected_model = model or groq_models[0]
        elif selected_provider == "github-models":
            github_models = [
                x.strip()
                for x in os.getenv(
                    "GITHUB_MODELS_LLM_MODELS",
                    "gpt-4o-mini,llama-2-7b,phi-3.5-mini",
                ).split(",")
                if x.strip()
            ]
            selected_model = model or github_models[0]
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
        provider_hint = _provider_retry_hint(provider)
        return {
            "result": (
                "目前選擇的模型暫時不可用。"
                f"{provider_hint} "
                f"Error: {exc}"
            )
        }
