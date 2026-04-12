import streamlit as st
import os
import hashlib
from pathlib import Path
from dotenv import load_dotenv
import streamlit.components.v1 as components

load_dotenv()

from core.document_processor import process_pdf
from services.vector_store import (
    save_to_chroma,
    get_vectorstore,
    is_document_embedded,
    clear_embedding_cache,
)
from services.llm_service import get_answer
from core.config import (
    EMBEDDING_PROVIDERS,
    LLM_PROVIDERS,
    get_available_models,
    get_runtime_status,
)

st.set_page_config(page_title="企業 AI 知識庫助手", layout="centered")
st.title("📄 企業級 RAG 知識庫 MVP")

_LOCAL_STORAGE_BRIDGE = components.declare_component(
    "local_storage_bridge",
    path=str(Path(__file__).parent / "components" / "local_storage_bridge"),
)

_API_KEY_FIELDS = {
    "google_api_key": "GOOGLE_API_KEY",
    "cohere_api_key": "COHERE_API_KEY",
    "together_api_key": "TOGETHER_API_KEY",
    "hf_api_key": "HF_API_KEY",
    "groq_api_key": "GROQ_API_KEY",
    "github_models_token": "GITHUB_MODELS_TOKEN",
}


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


def _clear_embedding_model_on_provider_change():
    if "embedding_model" in st.session_state:
        del st.session_state["embedding_model"]


def _clear_llm_model_on_provider_change():
    if "llm_model" in st.session_state:
        del st.session_state["llm_model"]


def _apply_api_keys_from_session_to_env():
    for field_key, env_key in _API_KEY_FIELDS.items():
        value = st.session_state.get(f"ui_{field_key}", "")
        if value:
            os.environ[env_key] = value


def _sync_api_keys_from_local_storage():
    stored_values = _LOCAL_STORAGE_BRIDGE(
        namespace="api_keys",
        keys=list(_API_KEY_FIELDS.keys()),
        key="api_keys_reader",
        default={},
    )
    if isinstance(stored_values, dict):
        for field_key, env_key in _API_KEY_FIELDS.items():
            ui_key = f"ui_{field_key}"
            value = stored_values.get(field_key, "")
            if value and not st.session_state.get(ui_key):
                st.session_state[ui_key] = value
            if value:
                os.environ[env_key] = value


_sync_api_keys_from_local_storage()


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

    with st.expander("API Key 快速設定（本次會話）", expanded=False):
        st.text_input("Google API Key", type="password", key="ui_google_api_key")
        st.text_input("Cohere API Key", type="password", key="ui_cohere_api_key")
        st.text_input("Together API Key", type="password", key="ui_together_api_key")
        st.text_input("HuggingFace API Key", type="password", key="ui_hf_api_key")
        st.text_input("Groq API Key", type="password", key="ui_groq_api_key")
        st.text_input("GitHub Models Token", type="password", key="ui_github_models_token")

        save_browser = st.button("儲存到瀏覽器 localStorage", use_container_width=True)
        apply_session = st.button("僅套用本次執行", use_container_width=True)
        clear_browser = st.button("清除瀏覽器已儲存 API Key", use_container_width=True)

        if save_browser:
            values = {
                field_key: st.session_state.get(f"ui_{field_key}", "")
                for field_key in _API_KEY_FIELDS
            }
            _LOCAL_STORAGE_BRIDGE(
                namespace="api_keys",
                keys=list(_API_KEY_FIELDS.keys()),
                writeValues=values,
                key="api_keys_writer",
                default={},
            )
            _apply_api_keys_from_session_to_env()
            st.success("已儲存到 browser localStorage，並套用到目前執行環境。")

        if apply_session:
            _apply_api_keys_from_session_to_env()
            st.success("已套用到目前執行環境（未改動 .env）。")

        if clear_browser:
            _LOCAL_STORAGE_BRIDGE(
                namespace="api_keys",
                keys=list(_API_KEY_FIELDS.keys()),
                clearKeys=list(_API_KEY_FIELDS.keys()),
                key="api_keys_clearer",
                default={},
            )
            for field_key, env_key in _API_KEY_FIELDS.items():
                st.session_state[f"ui_{field_key}"] = ""
                os.environ.pop(env_key, None)
            st.success("已清除瀏覽器 localStorage 內的 API Key。")

        st.caption(
            "儲存透明說明：按『儲存到瀏覽器 localStorage』後，金鑰儲存在瀏覽器端 localStorage，"
            "不會寫入專案檔案（如 .env）與資料庫。"
        )
        st.caption(
            "localStorage 位置：Browser DevTools > Application > Local Storage。"
            "鍵名格式：rag_project.api_keys.<provider_key>"
        )

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
        on_change=_clear_embedding_model_on_provider_change,
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
        on_change=_clear_llm_model_on_provider_change,
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
    st.caption("Replit 可能休眠；喚醒後若向量快取遺失，請重新執行 Embedding。")

    embedding_status = get_runtime_status("embedding", embedding_provider)
    llm_status = get_runtime_status("llm", llm_provider)

    if embedding_status:
        st.subheader("Embedding 狀態")
        st.text(_format_runtime_status(embedding_status))
    else:
        st.subheader("Embedding 狀態")
        st.text(_format_runtime_status(embedding_status))

    clear_selected_embedding_cache = st.button(
        "清除目前 Embedding 快取（Provider + Model）",
        use_container_width=True,
    )
    if clear_selected_embedding_cache:
        summary = clear_embedding_cache(
            provider=embedding_provider,
            model=embedding_model,
        )
        st.session_state.pop("indexed_signature", None)
        st.warning(
            f"已清除 {summary['provider']} / {summary['model']} 快取，"
            f"移除 {summary['removed_registry_entries']} 筆索引紀錄，"
            f"向量庫目錄重置: {'是' if summary['vector_dir_removed'] else '否'}。"
        )

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
        st.info("檔案或 Embedding 設定已變更，請按下『執行 Embedding』重建索引。")
    else:
        st.caption("使用既有索引（未重新向量化）：檔案內容與 Embedding 設定未變更。")

    do_embedding = st.button("執行 Embedding", type="primary", use_container_width=True)
    if do_embedding:
        progress = st.progress(0, text="開始處理文件...")
        with open(save_path, "wb") as f:
            f.write(file_bytes)
        progress.progress(20, text="已儲存檔案，準備解析 PDF...")
        cache_hit = is_document_embedded(
            file_hash=file_hash,
            provider=embedding_provider,
            model=embedding_model,
        )

        chunks = process_pdf(save_path)
        progress.progress(55, text=f"PDF 解析完成，切分 {len(chunks)} 個區塊...")

        if cache_hit:
            progress.progress(100, text="偵測到已存在索引，已採用本地切分內容並略過模型嵌入。")
            st.info("此文件已完成過相同 Embedding 設定，已直接重用既有向量索引。")
        else:
            for idx, chunk in enumerate(chunks):
                chunk.metadata = dict(chunk.metadata or {})
                chunk.metadata["source_file"] = uploaded_file.name
                chunk.metadata["file_hash"] = file_hash
                chunk.metadata["embedding_provider"] = embedding_provider
                chunk.metadata["embedding_model"] = embedding_model or "default"
                chunk.metadata["chunk_index"] = idx

            save_to_chroma(
                chunks,
                provider=embedding_provider,
                model=embedding_model,
                file_hash=file_hash,
                file_name=uploaded_file.name,
            )
            progress.progress(100, text="Embedding 與向量索引完成。")
        st.session_state["indexed_signature"] = index_signature
        st.success("索引建立完成，現在可以開始提問。")

    # 對話區
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    indexed_signature = st.session_state.get("indexed_signature")
    current_ready = indexed_signature == index_signature
    if not current_ready:
        st.warning("目前尚未完成此檔案/設定的索引，請先按『執行 Embedding』。")

    if prompt := st.chat_input("請問關於這份文件的任何問題？", disabled=not current_ready):
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