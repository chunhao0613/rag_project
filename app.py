import streamlit as st
import os
import hashlib
from dotenv import load_dotenv

load_dotenv()

from core.document_processor import process_pdf
from services.vector_store import save_to_chroma, get_vectorstore
from services.llm_service import get_answer
from core.config import (
    EMBEDDING_PROVIDERS,
    LLM_PROVIDERS,
    get_available_models,
    get_runtime_status,
)

st.set_page_config(page_title="企業 AI 知識庫助手", layout="centered")
st.title("📄 企業級 RAG 知識庫 MVP")


def _ordered_options(all_options, preferred_order):
    preferred = [x for x in preferred_order if x in all_options]
    remainder = [x for x in all_options if x not in preferred]
    return preferred + remainder


def _pick_default_embedding_provider(options):
    if not options:
        return None
    if os.getenv("GOOGLE_API_KEY", "").strip() and "google" in options:
        return "google"
    if os.getenv("COHERE_API_KEY", "").strip() and "cohere" in options:
        return "cohere"
    if os.getenv("TOGETHER_API_KEY", "").strip() and "together" in options:
        return "together"
    if os.getenv("HF_API_KEY", "").strip() and "huggingface" in options:
        return "huggingface"
    return options[0]


def _pick_default_llm_provider(options):
    if not options:
        return None
    if os.getenv("GITHUB_MODELS_TOKEN", "").strip() and "github-models" in options:
        return "github-models"
    if os.getenv("GROQ_API_KEY", "").strip() and "groq" in options:
        return "groq"
    if os.getenv("GOOGLE_API_KEY", "").strip() and "google" in options:
        return "google"
    if os.getenv("HF_API_KEY", "").strip() and "huggingface" in options:
        return "huggingface"
    return options[0]


def _mask_key_present(env_name):
    return bool(os.getenv(env_name, "").strip())


def _format_runtime_status(status):
    if not status:
        return "尚無執行資料（請先完成一次索引或問答）"

    lines = []
    status_value = status.get("status", "unknown")
    lines.append(f"狀態: {status_value}")

    if status.get("model"):
        lines.append(f"模型: {status['model']}")
    if status.get("backend"):
        lines.append(f"後端: {status['backend']}")
    if status.get("remaining_requests"):
        lines.append(f"剩餘請求: {status['remaining_requests']}")
    if status.get("remaining_tokens"):
        lines.append(f"剩餘 Tokens: {status['remaining_tokens']}")
    if status.get("prompt_tokens"):
        lines.append(f"Prompt Tokens: {status['prompt_tokens']}")
    if status.get("completion_tokens"):
        lines.append(f"Completion Tokens: {status['completion_tokens']}")
    if status.get("retry_after_seconds"):
        lines.append(f"建議重試秒數: {status['retry_after_seconds']}")
    if status.get("reason"):
        lines.append(f"原因: {status['reason']}")
    if status.get("error_message"):
        lines.append(f"錯誤訊息: {status['error_message']}")
    if status.get("updated_at"):
        lines.append(f"更新時間(UTC): {status['updated_at']}")

    return "\n".join(lines)

with st.sidebar:
    st.header("模型設定")

    with st.expander("如何選模型（建議流程）", expanded=False):
        st.markdown(
            "1. 中文 PDF 優先使用 Cohere `embed-multilingual-v3.0` 作 Embedding。\n"
            "2. 若要高成功率回覆，LLM 優先選 `github-models + gpt-4o-mini`。\n"
            "3. 若遇到配額或 400，先換模型再問一次，不必重傳 PDF。\n"
            "4. 只有檔案內容或 Embedding 設定改變才會重建索引。"
        )

    st.subheader("憑證狀態")
    st.markdown(
        "\n".join(
            [
                f"- Google API Key: {'已設定' if _mask_key_present('GOOGLE_API_KEY') else '未設定'}",
                f"- Cohere API Key: {'已設定' if _mask_key_present('COHERE_API_KEY') else '未設定'}",
                f"- Together API Key: {'已設定' if _mask_key_present('TOGETHER_API_KEY') else '未設定'}",
                f"- HuggingFace API Key: {'已設定' if _mask_key_present('HF_API_KEY') else '未設定'}",
                f"- Groq API Key: {'已設定' if _mask_key_present('GROQ_API_KEY') else '未設定'}",
                f"- GitHub Models Token: {'已設定' if _mask_key_present('GITHUB_MODELS_TOKEN') else '未設定'}",
            ]
        )
    )

    embedding_provider_options = _ordered_options(
        EMBEDDING_PROVIDERS,
        ["google", "cohere", "together", "huggingface", "local"],
    )
    default_embedding_provider = _pick_default_embedding_provider(embedding_provider_options)
    if (
        "embedding_provider" in st.session_state
        and st.session_state["embedding_provider"] not in embedding_provider_options
    ):
        del st.session_state["embedding_provider"]

    embedding_provider = st.selectbox(
        "Embedding Provider",
        embedding_provider_options,
        index=embedding_provider_options.index(default_embedding_provider) if default_embedding_provider else 0,
        key="embedding_provider",
    )
    embedding_model_options = get_available_models(embedding_provider, "embedding")
    if "embedding_model" in st.session_state and st.session_state["embedding_model"] not in embedding_model_options:
        del st.session_state["embedding_model"]
    embedding_model = st.selectbox(
        "Embedding Model",
        embedding_model_options,
        index=0 if embedding_model_options else None,
        key="embedding_model",
    )

    llm_provider_options = _ordered_options(
        LLM_PROVIDERS,
        ["github-models", "groq", "google", "huggingface"],
    )
    default_llm_provider = _pick_default_llm_provider(llm_provider_options)
    if "llm_provider" in st.session_state and st.session_state["llm_provider"] not in llm_provider_options:
        del st.session_state["llm_provider"]

    llm_provider = st.selectbox(
        "LLM Provider",
        llm_provider_options,
        index=llm_provider_options.index(default_llm_provider) if default_llm_provider else 0,
        key="llm_provider",
    )
    llm_model_options = get_available_models(llm_provider, "llm")
    if "llm_model" in st.session_state and st.session_state["llm_model"] not in llm_model_options:
        del st.session_state["llm_model"]
    llm_model = st.selectbox(
        "LLM Model",
        llm_model_options,
        index=0 if llm_model_options else None,
        key="llm_model",
    )

    if llm_provider == "github-models" and llm_model in {"llama-2-7b", "phi-3.5-mini"}:
        st.warning("此模型在 GitHub Models 可能回傳 400。建議先用 gpt-4o-mini。")

    if embedding_provider == "cohere" and embedding_model == "embed-english-v3.0":
        st.info("中文文件建議改用 embed-multilingual-v3.0 以提升檢索命中率。")

    st.caption("Quota 顯示說明：Google 無法預先查可用額度，僅在 429 時顯示重試資訊。")

    embedding_status = get_runtime_status("embedding", embedding_provider)
    llm_status = get_runtime_status("llm", llm_provider)

    if embedding_status:
        st.subheader("Embedding 狀態")
        st.text(_format_runtime_status(embedding_status))
    else:
        st.subheader("Embedding 狀態")
        st.text(_format_runtime_status(embedding_status))

    if llm_status:
        st.subheader("LLM 狀態")
        st.text(_format_runtime_status(llm_status))
    else:
        st.subheader("LLM 狀態")
        st.text(_format_runtime_status(llm_status))

# 介面配置
uploaded_file = st.file_uploader("上傳 PDF 文件", type="pdf")

if uploaded_file:
    file_bytes = uploaded_file.getvalue()
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    index_signature = f"{uploaded_file.name}:{file_hash}:{embedding_provider}:{embedding_model}"
    previous_signature = st.session_state.get("indexed_signature")
    needs_reindex = index_signature != previous_signature

    save_path = f"data/uploads/{uploaded_file.name}"
    if needs_reindex:
        with open(save_path, "wb") as f:
            f.write(file_bytes)

        with st.status("正在處理文件...", expanded=True) as status:
            st.write("解析 PDF 中...")
            chunks = process_pdf(save_path)
            st.write(f"切分完成，共 {len(chunks)} 個區塊。")

            st.write("寫入向量資料庫...")
            save_to_chroma(
                chunks,
                provider=embedding_provider,
                model=embedding_model,
            )
            status.update(label="文件處理完成！", state="complete", expanded=False)

        st.session_state["indexed_signature"] = index_signature
    else:
        st.caption("使用既有索引（未重新向量化）：檔案內容與 Embedding 設定未變更。")

    # 對話區
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("請問關於這份文件的任何問題？"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.chat_message("assistant"):
            # 取得答案
            db = get_vectorstore(provider=embedding_provider, model=embedding_model)
            response = get_answer(
                db,
                prompt,
                provider=llm_provider,
                model=llm_model,
            )
            answer = response["result"]
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})