import os
import streamlit as st
from dotenv import load_dotenv

from src.task10_generation import generate_stream_with_citation, generate_with_citation



load_dotenv()

st.set_page_config(
    page_title="Trợ lý RAG Du Lịch Việt Nam",
    page_icon="🏖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for enhanced aesthetics
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0.2rem;
    }
    .sub-title {
        color: #4B5563;
        font-size: 1rem;
        margin-bottom: 1.5rem;
    }
    .source-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        background-color: #E0E7FF;
        color: #3730A3;
        margin-right: 0.5rem;
    }
    .score-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        background-color: #FEF3C7;
        color: #92400E;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "messages" not in st.session_state:
    st.session_state.messages = []

# Sidebar Controls
with st.sidebar:
    st.title("⚙️ Cấu hình RAG")
    st.markdown("---")
    
    top_k = st.slider("Số lượng Chunks (Top-K)", min_value=1, max_value=10, value=5, step=1)
    
    provider = os.getenv("LLM_PROVIDER", "openai").upper()
    model = os.getenv("LLM_MODEL") or ("gpt-4o-mini" if provider == "OPENAI" else "gemini-2.0-flash")
    
    st.info(f"**LLM Provider:** {provider}\n\n**Model:** `{model}`")
    
    st.markdown("---")
    st.markdown("### 💡 Gợi ý câu hỏi:")
    sample_queries = [
        "Kinh nghiệm du lịch Phú Quốc mùa nào đẹp nhất?",
        "Đặc sản nổi tiếng ở Sa Pa gồm những món gì?",
        "Các điểm tham quan, vui chơi hấp dẫn tại Đà Nẵng?",
        "Mục tiêu quy hoạch phát triển du lịch Phú Quốc là gì?",
        "Cẩm nang du lịch Hà Giang cần lưu ý những gì?",
    ]
    for q in sample_queries:
        if st.button(q, use_container_width=True, key=f"btn_{q}"):
            st.session_state.messages.append({"role": "user", "content": q})
            st.rerun()

    st.markdown("---")
    if st.button("🗑️ Xóa lịch sử chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# Main Chat View
st.markdown('<div class="main-title">🏖️ Trợ lý Thông tin Du Lịch & Chính Sách</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-title">Hệ thống hỏi đáp thông minh kết hợp Hybrid Retrieval (Dense + BM25 RRF) với dữ liệu cẩm nang du lịch và văn bản quy hoạch.</div>',
    unsafe_allow_html=True,
)

def render_sources(sources: list[dict], retrieval_source: str):
    """Hiển thị danh sách nguồn trích dẫn chi tiết."""
    if not sources:
        return

    retrieval_labels = {
        "hybrid": "🔄 Hybrid Search (Dense + BM25)",
        "pageindex": "📑 PageIndex Fallback",
        "dense": "🧠 Semantic Search",
        "bm25": "🔍 Lexical Search",
        "none": "❌ Không có nguồn",
    }
    label = retrieval_labels.get(retrieval_source, f"🔍 {retrieval_source}")

    with st.expander(f"📚 Nguồn tham khảo ({len(sources)} chunks | Phương pháp: {label})", expanded=False):
        for idx, doc in enumerate(sources, 1):
            meta = doc.get("metadata", {})
            title = meta.get("title") or meta.get("source", f"Tài liệu {idx}")
            source_file = meta.get("source", "N/A")
            url = meta.get("url")
            score = doc.get("score", 0.0)
            method = doc.get("retrieval_method", "N/A")
            content = doc.get("content", "").strip()

            st.markdown(f"**{idx}. {title}**")
            cols = st.columns([2, 1, 1])
            with cols[0]:
                if url:
                    st.caption(f"🔗 [Link bài viết gốc]({url}) ({source_file})")
                else:
                    st.caption(f"📄 Nguồn: `{source_file}`")
            with cols[1]:
                st.caption(f"⚙️ Phương thức: `{method}`")
            with cols[2]:
                st.caption(f"🎯 Điểm số: `{score:.4f}`")

            st.code(content[:400] + ("..." if len(content) > 400 else ""), language="markdown")
            st.markdown("---")

# Render conversation history
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and "sources" in msg:
            render_sources(msg.get("sources", []), msg.get("retrieval_source", "hybrid"))

# Check if the last message is from user and needs assistant response
if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
    user_query = st.session_state.messages[-1]["content"]
    with st.chat_message("assistant"):
        with st.spinner("Đang tìm kiếm tài liệu liên quan..."):
            stream_gen, sources, retrieval_source = generate_stream_with_citation(user_query, top_k=top_k)

        full_answer = st.write_stream(stream_gen)
        render_sources(sources, retrieval_source)

        # Store in session state
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": full_answer,
                "sources": sources,
                "retrieval_source": retrieval_source,
            }
        )


# Chat Input
query = st.chat_input("Nhập câu hỏi của bạn về du lịch Việt Nam...")
if query:
    st.session_state.messages.append({"role": "user", "content": query})
    st.rerun()
