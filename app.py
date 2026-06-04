import streamlit as st
import pandas as pd

from src.multimodal_loader import extract_text_from_file
from src.chunking import chunk_text
from src.vector_db import create_vector_db, retrieve_chunks
from src.rag_pipeline import generate_answer
from src.evaluator import run_evaluation
from src.direct_answer import direct_answer_from_text
from src.config import (
    LLM_MODEL,
    EMBED_MODEL,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    N_RESULTS,
    TEMPERATURE
)


st.set_page_config(
    page_title="Multi-Modal RAG Research Assistant",
    page_icon="📄",
    layout="wide"
)


# =========================
# CSS
# =========================
st.markdown(
    """
    <style>
    .stApp {
        background: #f7f2eb;
        color: #142033;
    }

    header {
        visibility: hidden;
    }

    .main .block-container {
        max-width: 1180px;
        padding-top: 1.5rem;
        padding-bottom: 4rem;
    }

    section[data-testid="stSidebar"] {
        background: #fffaf4;
        border-right: 1px solid #eadfd3;
    }

    section[data-testid="stSidebar"] * {
        color: #142033;
    }

    .top-nav {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 22px;
        margin-bottom: 42px;
        border-bottom: 1px solid #e5d8ca;
    }

    .brand-title {
        font-family: Georgia, serif;
        font-size: 32px;
        font-weight: 900;
        color: #142033;
    }

    .brand-subtitle {
        font-size: 14px;
        color: #667085;
        margin-top: 2px;
    }

    .nav-menu {
        display: flex;
        align-items: center;
        gap: 28px;
        font-size: 16px;
        font-weight: 700;
        color: #142033;
    }

    .nav-button {
        background: #142033;
        color: white;
        padding: 14px 28px;
        border-radius: 6px;
        font-weight: 800;
    }

    .hero-label {
        color: #bd5c49;
        font-size: 13px;
        font-weight: 900;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 18px;
    }

    .hero-title {
        font-family: Georgia, serif;
        font-size: 48px;
        line-height: 1.14;
        font-weight: 900;
        color: #142033;
        letter-spacing: -1px;
        margin-bottom: 22px;
    }

    .hero-title span {
        color: #bd5c49;
        font-style: italic;
    }

    .hero-desc {
        font-size: 18px;
        line-height: 1.8;
        color: #475569;
        max-width: 620px;
        margin-bottom: 30px;
    }

    .preview-card {
        background: white;
        border-radius: 18px;
        padding: 18px;
        border: 1px solid #eadfd3;
        box-shadow: 0 26px 55px rgba(20, 32, 51, 0.14);
    }

    .preview-inner {
        background: linear-gradient(135deg, #142033, #243247);
        border-radius: 16px;
        padding: 30px;
        min-height: 350px;
        color: white;
    }

    .preview-small {
        color: #cbd5e1;
        font-size: 13px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        font-weight: 800;
        margin-bottom: 30px;
    }

    .preview-title {
        font-family: Georgia, serif;
        font-size: 32px;
        line-height: 1.25;
        font-weight: 900;
        color: white;
        margin-bottom: 18px;
    }

    .preview-text {
        font-size: 16px;
        line-height: 1.7;
        color: #d1d5db;
        margin-bottom: 24px;
    }

    .preview-step {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.13);
        border-radius: 12px;
        padding: 14px 16px;
        margin-bottom: 12px;
        color: #f8fafc;
        font-size: 15px;
    }

    .section-card {
        background: white;
        border: 1px solid #eadfd3;
        border-radius: 18px;
        padding: 30px;
        box-shadow: 0 18px 42px rgba(20, 32, 51, 0.08);
        margin-bottom: 28px;
    }

    .section-title {
        font-family: Georgia, serif;
        font-size: 32px;
        font-weight: 900;
        color: #142033;
        margin-bottom: 12px;
    }

    .section-text {
        font-size: 17px;
        line-height: 1.8;
        color: #475569;
    }

    .type-grid {
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 14px;
        margin-top: 20px;
    }

    .type-box {
        background: #faf7f2;
        border: 1px solid #eadfd3;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
        font-weight: 800;
        color: #142033;
    }

    .sidebar-box {
        background: white;
        border: 1px solid #eadfd3;
        border-radius: 16px;
        padding: 20px;
        margin-bottom: 18px;
        box-shadow: 0 10px 24px rgba(20, 32, 51, 0.05);
    }

    .sidebar-title {
        font-family: Georgia, serif;
        font-size: 23px;
        font-weight: 900;
        color: #142033;
        margin-bottom: 8px;
    }

    .sidebar-text {
        font-size: 15px;
        color: #64748b;
        line-height: 1.7;
    }

    [data-testid="stFileUploader"] {
        background: white;
        border: 1.5px dashed #c85f4b;
        border-radius: 16px;
        padding: 24px;
        box-shadow: 0 12px 28px rgba(20, 32, 51, 0.06);
    }

    [data-testid="stChatMessage"] {
        background: white;
        border: 1px solid #eadfd3;
        border-radius: 16px;
        padding: 18px;
        box-shadow: 0 10px 26px rgba(20, 32, 51, 0.05);
        margin-bottom: 14px;
    }

    [data-testid="stChatInput"] {
        background: white;
        border-radius: 14px;
        border: 1px solid #d9c9b8;
        box-shadow: 0 12px 28px rgba(20, 32, 51, 0.06);
    }

    .stButton button {
        background: #142033;
        color: white;
        border-radius: 8px;
        border: none;
        min-height: 46px;
        font-weight: 800;
    }

    .stButton button:hover {
        background: #c85f4b;
        color: white;
    }

    h1, h2, h3 {
        color: #142033 !important;
    }

    @media (max-width: 900px) {
        .hero-title {
            font-size: 38px;
        }

        .top-nav {
            display: block;
        }

        .nav-menu {
            margin-top: 18px;
            flex-wrap: wrap;
            gap: 14px;
        }

        .type-grid {
            grid-template-columns: 1fr;
        }
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# SESSION STATE
# =========================
defaults = {
    "messages": [],
    "collection": None,
    "file_name": "",
    "file_type": "",
    "extracted_text": "",
    "chunk_count": 0,
    "logged_in": False,
    "user_name": "",
    "user_email": "",
    "user_phone": "",
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================
# SIDEBAR
# =========================
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-box">
            <div class="sidebar-title">Tài khoản người dùng</div>
            <div class="sidebar-text">
                Nhập thông tin để lưu phiên làm việc hiện tại.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if not st.session_state.logged_in:
        with st.form("login_form"):
            name = st.text_input("Họ và tên")
            email = st.text_input("Email")
            phone = st.text_input("Số điện thoại")
            submitted = st.form_submit_button("Đăng nhập")

            if submitted:
                if not name.strip():
                    st.warning("Vui lòng nhập họ và tên.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user_name = name
                    st.session_state.user_email = email
                    st.session_state.user_phone = phone
                    st.rerun()
    else:
        st.markdown(
            f"""
            <div class="sidebar-box">
                <div class="sidebar-title">Xin chào, {st.session_state.user_name}</div>
                <div class="sidebar-text">
                    Email: {st.session_state.user_email if st.session_state.user_email else "Chưa có"}<br>
                    SĐT: {st.session_state.user_phone if st.session_state.user_phone else "Chưa có"}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        if st.button("Đăng xuất"):
            st.session_state.logged_in = False
            st.session_state.user_name = ""
            st.session_state.user_email = ""
            st.session_state.user_phone = ""
            st.rerun()

    st.markdown("### Cấu hình hiện tại")
    st.write(f"LLM: `{LLM_MODEL}`")
    st.write(f"Embedding: `{EMBED_MODEL}`")
    st.write(f"Chunk size: `{CHUNK_SIZE}`")
    st.write(f"Overlap: `{CHUNK_OVERLAP}`")
    st.write(f"n_results: `{N_RESULTS}`")
    st.write(f"Temperature: `{TEMPERATURE}`")

    if st.button("Xóa lịch sử trò chuyện"):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        """
        <div class="sidebar-box">
            <div class="sidebar-title">Pipeline</div>
            <div class="sidebar-text">
                File → Extract Text → Chunking → Embedding → ChromaDB → Retrieval → LLM Answer
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# TOP NAVIGATION
# =========================
st.markdown(
    """
    <div class="top-nav">
        <div>
            <div class="brand-title">Multi-Modal RAG Research Assistant</div>
            <div class="brand-subtitle">PDF · Image · Audio · Video · RAG Evaluation</div>
        </div>
        <div class="nav-menu">
            <div>Upload</div>
            <div>Chatbot</div>
            <div>Evaluation</div>
            <div>Report</div>
            <div class="nav-button">Research Mode</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# HERO
# =========================
left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.markdown(
        """
        <div class="hero-label">Ứng dụng RAG đa phương thức</div>
        <div class="hero-title">
            Hỏi đáp dữ liệu và <span>đánh giá cấu hình RAG</span>
        </div>
        <div class="hero-desc">
            Ứng dụng cho phép tải lên PDF, văn bản, hình ảnh, âm thanh hoặc video.
            Sau đó hệ thống trích xuất nội dung, chia chunk, tạo embedding, truy xuất context 
            và dùng LLM để trả lời. Chế độ nghiên cứu giúp kiểm thử câu hỏi và lưu kết quả đánh giá.
        </div>
        """,
        unsafe_allow_html=True
    )

with right:
    st.markdown(
        """
        <div class="preview-card">
            <div class="preview-inner">
                <div class="preview-small">RAG Research System</div>
                <div class="preview-title">Một chatbot cho nhiều loại dữ liệu</div>
                <div class="preview-text">
                    Phù hợp để demo project và phát triển thành báo cáo nghiên cứu về hiệu quả các cấu hình RAG.
                </div>
                <div class="preview-step">1. Upload nhiều loại file</div>
                <div class="preview-step">2. Hỏi đáp bằng RAG Pipeline</div>
                <div class="preview-step">3. Chạy bộ câu hỏi đánh giá</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# SUPPORTED TYPES
# =========================
st.markdown(
    """
    <div class="section-card">
        <div class="section-title">Loại dữ liệu được hỗ trợ</div>
        <div class="section-text">
            App chuyển mọi dữ liệu đầu vào về dạng văn bản trước khi đưa vào RAG.
            Với PDF scan, ảnh và video, hệ thống dùng vision model để đọc/mô tả nội dung.
        </div>
        <div class="type-grid">
            <div class="type-box">PDF</div>
            <div class="type-box">TXT</div>
            <div class="type-box">Ảnh</div>
            <div class="type-box">Âm thanh</div>
            <div class="type-box">Video</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# UPLOAD FILE
# =========================
st.markdown("## 1. Tải file lên hệ thống")

uploaded_file = st.file_uploader(
    "Chọn file PDF, TXT, ảnh, audio hoặc video",
    type=[
        "pdf", "txt",
        "png", "jpg", "jpeg", "webp",
        "mp3", "wav", "m4a",
        "mp4", "mov", "avi", "mkv"
    ]
)

if uploaded_file is not None:
    # Nếu upload file mới thì reset dữ liệu cũ
    if st.session_state.file_name != uploaded_file.name:
        st.session_state.collection = None
        st.session_state.messages = []
        st.session_state.file_name = uploaded_file.name
        st.session_state.file_type = ""
        st.session_state.extracted_text = ""
        st.session_state.chunk_count = 0

    if st.session_state.collection is None:
        with st.spinner("Đang kiểm tra và xử lý file. Audio/video/PDF scan có thể mất lâu hơn..."):
            file_type, text, status_message = extract_text_from_file(uploaded_file)

            st.session_state.file_type = file_type
            st.session_state.extracted_text = text

            if not text.strip():
                st.error(status_message)
            else:
                chunks = chunk_text(text)

                if not chunks:
                    st.error("Không tạo được chunk từ nội dung đã trích xuất.")
                else:
                    try:
                        collection = create_vector_db(chunks)

                        st.session_state.collection = collection
                        st.session_state.chunk_count = len(chunks)

                        st.success(status_message)
                        st.info(f"Loại dữ liệu: {file_type} | Số chunk đã tạo: {len(chunks)}")

                    except Exception as e:
                        st.error(f"Lỗi khi tạo vector database: {e}")


if st.session_state.file_name:
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">File đang sử dụng</div>
            <div class="section-text">
                Tên file: <b>{st.session_state.file_name}</b><br>
                Loại dữ liệu: <b>{st.session_state.file_type}</b><br>
                Số chunk: <b>{st.session_state.chunk_count}</b>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    with st.expander("Xem nội dung đã trích xuất"):
        if st.session_state.extracted_text:
            st.write(st.session_state.extracted_text[:5000])
        else:
            st.write("Chưa có nội dung được trích xuất.")


# =========================
# CHAT
# =========================
st.markdown("## 2. Hỏi đáp với dữ liệu")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


question = st.chat_input("Nhập câu hỏi của bạn về file đã tải lên...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.write(question)

    if st.session_state.collection is None:
        answer = "Bạn cần tải file lên và chờ hệ thống xử lý xong trước khi đặt câu hỏi."
    else:
        # Bước 1: Trả lời trực tiếp cho câu hỏi về SĐT/Zalo/email
        direct_answer = direct_answer_from_text(
            question=question,
            extracted_text=st.session_state.extracted_text
        )

        if direct_answer:
            answer = direct_answer
        else:
            # Bước 2: Nếu không phải câu hỏi dạng số/email thì dùng RAG
            with st.spinner("Đang tìm thông tin liên quan và tạo câu trả lời..."):
                retrieved_chunks = retrieve_chunks(
                    collection=st.session_state.collection,
                    question=question,
                    n_results=N_RESULTS
                )

                with st.expander("Xem các đoạn dữ liệu chatbot đã tìm thấy"):
                    for i, chunk in enumerate(retrieved_chunks, start=1):
                        st.markdown(f"**Chunk {i}:**")
                        st.write(chunk[:1000])
                        st.markdown("---")

                answer = generate_answer(question, retrieved_chunks)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

    with st.chat_message("assistant"):
        st.write(answer)


# =========================
# EVALUATION MODE
# =========================
st.markdown("## 3. Chế độ đánh giá nghiên cứu")

st.markdown(
    """
    Chế độ này dùng file `evaluation_questions.csv` để chạy một bộ câu hỏi test.
    Kết quả sẽ được lưu vào `evaluation_results.csv`.
    Sau đó nhóm chấm điểm thủ công theo các tiêu chí:
    correctness, groundedness, completeness, clarity, refusal.
    """
)

if st.button("Chạy đánh giá nghiên cứu"):
    if st.session_state.collection is None:
        st.warning("Bạn cần upload và xử lý file trước khi chạy đánh giá.")
    else:
        try:
            with st.spinner("Đang chạy bộ câu hỏi đánh giá..."):
                result_df = run_evaluation(
                    collection=st.session_state.collection,
                    questions_csv_path="evaluation_questions.csv"
                )

            st.success("Đã chạy đánh giá xong. Kết quả lưu tại evaluation_results.csv")
            st.dataframe(result_df)

        except FileNotFoundError:
            st.error("Chưa tìm thấy file evaluation_questions.csv.")
        except Exception as e:
            st.error(f"Lỗi khi chạy đánh giá: {e}")


try:
    result_df = pd.read_csv("evaluation_results.csv")
    with st.expander("Xem evaluation_results.csv hiện tại"):
        st.dataframe(result_df)
except Exception:
    pass