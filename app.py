import streamlit as st
import pandas as pd
import ollama

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
# CSS FIX FONT TIẾNG VIỆT + KHÔNG LỖI ICON UPLOAD
# =========================
st.markdown(
    """
    <style>
    html, body, .stApp, .stApp p, .stApp div, .stApp span, .stApp label,
    .stApp button, .stApp input, .stApp textarea {
        font-family: Arial, "Segoe UI", sans-serif;
    }

    [data-testid="stFileUploader"] svg,
    [data-testid="stFileUploader"] span[data-testid="stIconMaterial"],
    span[data-testid="stIconMaterial"],
    .material-symbols-rounded,
    .material-icons {
        font-family: "Material Symbols Rounded", "Material Icons" !important;
        font-weight: normal !important;
        font-style: normal !important;
        line-height: 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        display: inline-block !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        -webkit-font-feature-settings: "liga" !important;
        -webkit-font-smoothing: antialiased !important;
    }

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
        font-size: 32px;
        font-weight: 900;
        color: #142033;
        letter-spacing: -0.5px;
    }

    .brand-subtitle {
        font-size: 14px;
        color: #667085;
        margin-top: 4px;
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
        font-size: 48px;
        line-height: 1.18;
        font-weight: 900;
        color: #142033;
        letter-spacing: -1px;
        margin-bottom: 22px;
    }

    .hero-title span {
        color: #bd5c49;
        font-style: normal;
        font-weight: 900;
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
        font-size: 32px;
        line-height: 1.3;
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
        letter-spacing: -0.5px;
    }

    p, div, span, label {
        font-variant-ligatures: none;
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
# HELPER FUNCTIONS
# =========================

def contains_chinese(text: str) -> bool:
    """
    Kiểm tra text có ký tự tiếng Trung hay không.
    """
    if not text:
        return False

    for char in text:
        if "\u4e00" <= char <= "\u9fff":
            return True

    return False


def force_vietnamese_text(text: str) -> str:
    """
    Ép nội dung phân tích ảnh về tiếng Việt.
    Dùng khi vision model trả lẫn tiếng Trung.
    """
    if not text or not text.strip():
        return text

    if not contains_chinese(text):
        return text

    prompt = f"""
Bạn là hệ thống biên tập tiếng Việt.

Hãy viết lại nội dung sau HOÀN TOÀN bằng TIẾNG VIỆT.

YÊU CẦU BẮT BUỘC:
- Không được để lại bất kỳ chữ tiếng Trung nào.
- Không được để lại câu tiếng Trung nào.
- Dịch toàn bộ phần tiếng Trung sang tiếng Việt.
- Được giữ nguyên các nhãn kỹ thuật tiếng Anh như:
  File Document, Vector Database, Search, Retriever, Question, Prompt, Vicuna LLM, Answer, Output.
- Không thêm thông tin mới.
- Không bịa.
- Giữ cấu trúc đánh số 1, 2, 3, 4, 5 nếu có.
- Viết rõ ràng, dễ hiểu.

Nội dung cần sửa:
{text}

Bản tiếng Việt:
"""

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0}
        )

        result = response.get("message", {}).get("content", "")

        if result and result.strip():
            result = result.strip()

            if contains_chinese(result):
                second_prompt = f"""
Nội dung sau vẫn còn tiếng Trung. Hãy dịch lại toàn bộ sang tiếng Việt.
Không được để lại bất kỳ ký tự tiếng Trung nào.
Không thêm thông tin mới.
Không bịa.

Nội dung:
{result}

Bản tiếng Việt hoàn chỉnh:
"""
                second_response = ollama.chat(
                    model=LLM_MODEL,
                    messages=[
                        {"role": "user", "content": second_prompt}
                    ],
                    options={"temperature": 0}
                )

                second_result = second_response.get("message", {}).get("content", "")

                if second_result and second_result.strip():
                    return second_result.strip()

            return result

        return text

    except Exception:
        return text


def is_image_question(question: str) -> bool:
    """
    Nhận diện câu hỏi đang hỏi về ảnh/sơ đồ/slide.
    Nếu đúng thì ưu tiên dùng last_image_text.
    """
    if not question:
        return False

    q = question.lower()

    keywords = [
        "ảnh", "hình", "hình ảnh", "ảnh vừa tải", "hình vừa tải",
        "ảnh mới nhất", "hình mới nhất", "sơ đồ", "biểu đồ", "slide",
        "screenshot", "nội dung ảnh", "ảnh nói gì", "hình nói gì",
        "tóm tắt ảnh", "tóm tắt hình", "giải thích ảnh",
        "giải thích hình", "giải thích sơ đồ", "trong ảnh",
        "trong hình"
    ]

    return any(keyword in q for keyword in keywords)


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
    "chat_image_name": "",
    "last_image_text": "",
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
                <div class="preview-small">RAG RESEARCH SYSTEM</div>
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
# UPLOAD FILE CHÍNH
# =========================

st.markdown("## 1. Tải file lên hệ thống")

uploaded_file = st.file_uploader(
    "Chọn file PDF, TXT, ảnh, audio hoặc video",
    type=[
        "pdf", "txt",
        "png", "jpg", "jpeg", "webp",
        "mp3", "wav", "m4a",
        "mp4", "mov", "avi", "mkv"
    ],
    key="main_file_uploader"
)

if uploaded_file is not None:
    if st.session_state.file_name != uploaded_file.name:
        st.session_state.collection = None
        st.session_state.messages = []
        st.session_state.file_name = uploaded_file.name
        st.session_state.file_type = ""
        st.session_state.extracted_text = ""
        st.session_state.chunk_count = 0
        st.session_state.last_image_text = ""
        st.session_state.chat_image_name = ""

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
            preview_text = st.session_state.extracted_text[:5000]

            st.text_area(
                "Nội dung trích xuất",
                value=preview_text,
                height=300
            )

            if len(st.session_state.extracted_text) > 5000:
                st.info("Nội dung dài hơn 5000 ký tự, chỉ đang hiển thị phần đầu để dễ xem.")
        else:
            st.write("Chưa có nội dung được trích xuất.")


# =========================
# CHAT
# =========================

st.markdown("## 2. Hỏi đáp với dữ liệu")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


# =========================
# UPLOAD ẢNH BỔ SUNG
# =========================

st.markdown("### Tải ảnh nhanh trong phần hỏi đáp")

chat_image = st.file_uploader(
    "Chọn ảnh để hỏi nhanh",
    type=["png", "jpg", "jpeg", "webp"],
    key="chat_image_uploader"
)

if chat_image is not None:
    if st.session_state.chat_image_name != chat_image.name:
        st.session_state.chat_image_name = chat_image.name

        with st.spinner("Đang đọc nội dung ảnh và thêm vào dữ liệu hiện tại..."):
            file_type, image_text, status_message = extract_text_from_file(chat_image)

            if not image_text.strip():
                st.error(status_message)

            elif image_text.startswith("[VISION ERROR]"):
                st.error(image_text)

            else:
                image_text = force_vietnamese_text(image_text)
                st.session_state.last_image_text = image_text

                if st.session_state.extracted_text.strip():
                    combined_text = (
                        st.session_state.extracted_text
                        + "\n\n==============================\n"
                        + "NGUỒN: ẢNH BỔ SUNG\n"
                        + "==============================\n"
                        + image_text
                    )
                else:
                    combined_text = (
                        "==============================\n"
                        + "NGUỒN: ẢNH BỔ SUNG\n"
                        + "==============================\n"
                        + image_text
                    )

                st.session_state.extracted_text = combined_text
                st.session_state.file_type = "Combined Data"

                if st.session_state.file_name:
                    st.session_state.file_name = (
                        st.session_state.file_name + " + " + chat_image.name
                    )
                else:
                    st.session_state.file_name = chat_image.name

                chunks = chunk_text(combined_text)

                if not chunks:
                    st.error("Không tạo được chunk từ nội dung ảnh.")
                else:
                    try:
                        collection = create_vector_db(chunks)

                        st.session_state.collection = collection
                        st.session_state.chunk_count = len(chunks)

                        st.success("Đã xử lý ảnh và thêm vào dữ liệu hiện tại.")
                        st.info(f"Đã cập nhật dữ liệu | Số chunk mới: {len(chunks)}")

                    except Exception as e:
                        st.error(f"Lỗi khi tạo vector database sau khi thêm ảnh: {e}")

if st.session_state.last_image_text:
    with st.expander("Xem nội dung ảnh mới nhất đã trích xuất"):
        fixed_image_text = force_vietnamese_text(st.session_state.last_image_text)
        st.session_state.last_image_text = fixed_image_text

        st.text_area(
            "Nội dung ảnh",
            value=fixed_image_text[:5000],
            height=260
        )


# =========================
# QUESTION ANSWERING
# =========================

question = st.chat_input("Nhập câu hỏi của bạn về file hoặc ảnh đã tải lên...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.write(question)

    if st.session_state.collection is None:
        answer = "Bạn cần tải file hoặc ảnh lên và chờ hệ thống xử lý xong trước khi đặt câu hỏi."

    else:
        direct_answer = direct_answer_from_text(
            question=question,
            extracted_text=st.session_state.extracted_text
        )

        if direct_answer:
            answer = direct_answer

        elif is_image_question(question) and st.session_state.last_image_text.strip():
            image_context = st.session_state.last_image_text
            image_context = force_vietnamese_text(image_context)
            st.session_state.last_image_text = image_context

            with st.expander("Xem nội dung ảnh đã trích xuất", expanded=True):
                st.text_area(
                    "Nội dung ảnh",
                    value=image_context,
                    height=260
                )

            if image_context.startswith("[VISION ERROR]"):
                answer = "Không thể phân tích ảnh vì model đọc ảnh đang lỗi:\n\n" + image_context

            else:
                image_question = f"""
Chỉ dựa trên nội dung ảnh đã trích xuất dưới đây để trả lời bằng tiếng Việt.

Câu hỏi: {question}

Nội dung ảnh:
{image_context}

Yêu cầu:
- Trả lời đúng trọng tâm câu hỏi.
- Nếu là sơ đồ thì giải thích theo luồng.
- Không bịa thêm thông tin ngoài nội dung ảnh.
"""
                answer = generate_answer(
                    image_question,
                    [image_context]
                )

        else:
            with st.spinner("Đang tìm thông tin liên quan và tạo câu trả lời..."):
                retrieved_chunks = retrieve_chunks(
                    collection=st.session_state.collection,
                    question=question,
                    n_results=N_RESULTS
                )

                if st.session_state.last_image_text.strip():
                    fixed_image_text = force_vietnamese_text(st.session_state.last_image_text)
                    st.session_state.last_image_text = fixed_image_text
                    retrieved_chunks = [fixed_image_text] + retrieved_chunks

                with st.expander("Xem các đoạn dữ liệu chatbot đã tìm thấy"):
                    for i, chunk in enumerate(retrieved_chunks, start=1):
                        st.markdown(f"**Chunk {i}:**")
                        st.text_area(
                            f"Nội dung chunk {i}",
                            value=chunk[:1200],
                            height=180
                        )
                        st.markdown("---")

                combined_question = f"""
Trả lời bằng tiếng Việt dựa trên dữ liệu đã truy xuất.
Nếu có nội dung ảnh thì hãy kết hợp cả nội dung ảnh và nội dung file.
Câu hỏi: {question}
"""

                answer = generate_answer(combined_question, retrieved_chunks)

    answer = force_vietnamese_text(answer)

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