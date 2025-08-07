import os
import queue
import re
import threading
import uuid
import requests
import streamlit as st

from embed_app import embedchain_bot

# ------------------ App Initialization ------------------ #

def get_ec_app():
    if "app_id" not in st.session_state:
        st.session_state.app_id = str(uuid.uuid4())
    if "app" not in st.session_state:
        app_id = st.session_state.app_id
        app = embedchain_bot(app_id=app_id)
        st.session_state.app = app
    return st.session_state.app

# ------------------ Streamlit UI ------------------ #

st.set_page_config(page_title="Policy Chatbot", layout="wide")
app = get_ec_app()

# Upload PDFs
pdf_files = st.sidebar.file_uploader(
    "📄 Upload your PDF files", accept_multiple_files=True, type="pdf", key="pdf_uploader"
)
uploaded_pdf_names = st.session_state.get("uploaded_pdf_names", [])

for pdf_file in pdf_files:
    file_name = pdf_file.name
    if file_name in uploaded_pdf_names:
        continue

    try:
        response = requests.post(
            url="http://localhost:8001/document/document/upload",
            files={"file": (file_name, pdf_file.getvalue(), "application/pdf")},
            data={"user_id": "lakshma", "session_id": "lakshma"},
        )

        if response.status_code == 200:
            st.success(f"✅ Uploaded {file_name} to backend.")
            uploaded_pdf_names.append(file_name)
        else:
            st.error(f"❌ Failed to upload {file_name} — {response.text}")

    except Exception as e:
        st.error(f"❌ Error uploading {file_name}: {e}")

st.session_state["uploaded_pdf_names"] = uploaded_pdf_names

# ------------------ Chatbot Messages ------------------ #

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": """Hi! I'm a chatbot powered by AI, which can answer questions about your PDF documents.  
📥 Upload your PDFs and ask me anything!"""
    }]

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ------------------ Chat Input ------------------ #

if prompt := st.chat_input("Ask me anything!"):
    app = get_ec_app()

    with st.chat_message("user"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        st.markdown(prompt)

    with st.chat_message("assistant"):
        msg_placeholder = st.empty()
        msg_placeholder.markdown("Thinking... 🤔")
        full_response = ""
        q = queue.Queue()

        def app_response(results_dict):
            try:
                response = requests.post(
                    "http://127.0.0.1:8001/chat/",
                    json={
                        "user_id": "lakshma",
                        "session_id": "lakshma",
                        "question": prompt
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    print("🔍 Raw response from backend:", data)  # Debug log
                    results_dict["answer"] = data.get("answer")  # Show as-is
                    results_dict["citations"] = data.get("citations", [])
                else:
                    results_dict["answer"] = f"❌ Failed with status code {response.status_code}"
                    results_dict["citations"] = []

            except Exception as e:
                results_dict["answer"] = f"❌ Exception during API call: {e}"
                results_dict["citations"] = []

        results = {}
        thread = threading.Thread(target=app_response, args=(results,))
        thread.start()

        while thread.is_alive():
            try:
                chunk = q.get(timeout=0.1)
                full_response += chunk
                msg_placeholder.markdown(full_response)
            except queue.Empty:
                continue

        thread.join()
        answer = results.get("answer")
        citations = results.get("citations", [])

        if answer:
            full_response += answer
        else:
            full_response += "⚠️ No answer received from backend."

        if citations and "Answer not found in the document." not in answer:
            full_response += "\n\n**Sources**:\n"
            source_pages = {}
            for source_data in citations:
                source_url = source_data.get("url", "Unknown source")
                page = source_data.get("page", "N/A")
                match = re.search(r"([^/]+)\.[^\.]+\.pdf$", source_url)
                source_name = match.group(1) + ".pdf" if match else source_url
                source_pages.setdefault(source_name, set()).add(page)

            for source, pages in source_pages.items():
                pages_str = ', '.join(map(str, sorted(pages)))
                full_response += f"- {source} — Pages: {pages_str}\n"

        msg_placeholder.markdown(full_response)
        st.session_state.messages.append({"role": "assistant", "content": full_response})