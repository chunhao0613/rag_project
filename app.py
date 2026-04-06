import streamlit as st
import os
from dotenv import load_dotenv
from core.document_processor import process_pdf
from services.vector_store import save_to_chroma, get_vectorstore
from services.llm_service import get_answer

load_dotenv()

st.set_page_config(page_title="企業 AI 知識庫助手", layout="centered")
st.title("📄 企業級 RAG 知識庫 MVP")

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
        vectorstore = save_to_chroma(chunks)
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
            db = get_vectorstore()
            response = get_answer(db, prompt)
            answer = response["result"]
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})