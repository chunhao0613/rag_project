import streamlit as st
import os
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

with st.sidebar:
    st.header("模型設定")

    embedding_provider = st.selectbox(
        "Embedding Provider",
        EMBEDDING_PROVIDERS,
        index=0,
        key="embedding_provider",
    )
    embedding_model_options = get_available_models(embedding_provider, "embedding")
    embedding_model = st.selectbox(
        "Embedding Model",
        embedding_model_options,
        index=0 if embedding_model_options else None,
        key="embedding_model",
    )

    llm_provider = st.selectbox(
        "LLM Provider",
        LLM_PROVIDERS,
        index=0,
        key="llm_provider",
    )
    llm_model_options = get_available_models(llm_provider, "llm")
    llm_model = st.selectbox(
        "LLM Model",
        llm_model_options,
        index=0 if llm_model_options else None,
        key="llm_model",
    )

    st.caption("Quota 顯示說明：Google 無法預先查可用額度，僅在 429 時顯示重試資訊。")

    embedding_status = get_runtime_status("embedding", embedding_provider)
    llm_status = get_runtime_status("llm", llm_provider)

    if embedding_status:
        st.subheader("Embedding 狀態")
        st.json(embedding_status)

    if llm_status:
        st.subheader("LLM 狀態")
        st.json(llm_status)

# 介面配置
uploaded_file = st.file_uploader("上傳 PDF 文件", type="pdf")

if uploaded_file:
    # 儲存上傳檔案
    with open(f"data/uploads/{uploaded_file.name}", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    with st.status("正在處理文件...", expanded=True) as status:
        st.write("解析 PDF 中...")
        chunks = process_pdf(f"data/uploads/{uploaded_file.name}")
        st.write(f"切分完成，共 {len(chunks)} 個區塊。")
        
        st.write("寫入向量資料庫...")
        vectorstore = save_to_chroma(
            chunks,
            provider=embedding_provider,
            model=embedding_model,
        )
        status.update(label="文件處理完成！", state="complete", expanded=False)

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