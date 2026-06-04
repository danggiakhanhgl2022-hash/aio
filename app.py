import streamlit as st
import tempfile

from src.pdf_loader import read_pdf
from src.chunking import chunk_text
from src.vector_db import create_vector_db, retrieve_chunks
from src.rag_pipeline import generate_answer


st.set_page_config(
    page_title="RAG PDF Assistant",
    page_icon="📄",
    layout="wide"
)


# =========================
# CSS STYLE
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
        font-size: 54px;
        line-height: 1.12;
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

    .hero-actions {
        display: flex;
        gap: 16px;
        margin-top: 22px;
    }

    .btn-main {
        background: #c85f4b;
        color: white;
        padding: 16px 26px;
        border-radius: 8px;
        font-weight: 800;
        box-shadow: 0 14px 28px rgba(200, 95, 75, 0.22);
    }

    .btn-dark {
        background: #142033;
        color: white;
        padding: 16px 26px;
        border-radius: 8px;
        font-weight: 800;
        box-shadow: 0 14px 28px rgba(20, 32, 51, 0.18);
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
        min-height: 360px;
        color: white;
    }

    .preview-small {
        color: #cbd5e1;
        font-size: 13px;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        font-weight: 800;
        margin-bottom: 32px;
    }

    .preview-title {
        font-family: Georgia, serif;
        font-size: 34px;
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

    .stats-row {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 28px;
        margin-top: 58px;
        margin-bottom: 56px;
    }

    .stat-card {
        border-left: 1px solid #ddcfc0;
        padding-left: 26px;
    }

    .stat-number {
        font-family: Georgia, serif;
        font-size: 42px;
        font-weight: 900;
        color: #142033;
        margin-bottom: 8px;
    }

    .stat-label {
        font-size: 16px;
        color: #64748b;
        font-weight: 650;
    }

    .section-card {
        background: white;
        border: 1px solid #eadfd3;
        border-radius: 18px;
        padding: 32px;
        box-shadow: 0 18px 42px rgba(20, 32, 51, 0.08);
        margin-bottom: 30px;
    }

    .section-title {
        font-family: Georgia, serif;
        font-size: 34px;
        font-weight: 900;
        color: #142033;
        margin-bottom: 12px;
    }

    .section-text {
        font-size: 17px;
        line-height: 1.8;
        color: #475569;
    }

    .pipeline-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 16px;
        margin-top: 24px;
    }

    .pipeline-item {
        background: #faf7f2;
        border: 1px solid #eadfd3;
        border-radius: 14px;
        padding: 20px;
    }

    .pipeline-num {
        font-family: Georgia, serif;
        font-size: 28px;
        font-weight: 900;
        color: #bd5c49;
        margin-bottom: 8px;
    }

    .pipeline-title {
        font-size: 17px;
        font-weight: 850;
        color: #142033;
        margin-bottom: 8px;
    }

    .pipeline-desc {
        font-size: 15px;
        color: #64748b;
        line-height: 1.6;
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

    .footer {
        text-align: center;
        font-size: 14px;
        color: #64748b;
        margin-top: 40px;
    }

    @media (max-width: 900px) {
        .hero-title {
            font-size: 40px;
        }

        .top-nav {
            display: block;
        }

        .nav-menu {
            margin-top: 18px;
            flex-wrap: wrap;
            gap: 14px;
        }

        .stats-row {
            grid-template-columns: 1fr;
        }

        .pipeline-grid {
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
if "messages" not in st.session_state:
    st.session_state.messages = []

if "collection" not in st.session_state:
    st.session_state.collection = None

if "pdf_name" not in st.session_state:
    st.session_state.pdf_name = None

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "user_name" not in st.session_state:
    st.session_state.user_name = ""

if "user_email" not in st.session_state:
    st.session_state.user_email = ""

if "user_phone" not in st.session_state:
    st.session_state.user_phone = ""


# =========================
# SIDEBAR LOGIN
# =========================
with st.sidebar:
    st.markdown(
        """
        <div class="sidebar-box">
            <div class="sidebar-title">Tài khoản người dùng</div>
            <div class="sidebar-text">
                Nhập thông tin để lưu phiên làm việc và cá nhân hóa trải nghiệm sử dụng.
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
                if name.strip() == "":
                    st.warning("Vui lòng nhập họ và tên.")
                else:
                    st.session_state.logged_in = True
                    st.session_state.user_name = name
                    st.session_state.user_email = email
                    st.session_state.user_phone = phone
                    st.success("Đăng nhập thành công.")
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

    st.markdown("### Cấu hình trả lời")

    n_results = st.slider(
        "Số đoạn tài liệu dùng để trả lời",
        min_value=1,
        max_value=6,
        value=3
    )

    st.caption("Mặc định 3 đoạn là phù hợp để câu trả lời có đủ ngữ cảnh.")

    if st.button("Xóa lịch sử trò chuyện"):
        st.session_state.messages = []
        st.rerun()

    st.markdown(
        """
        <div class="sidebar-box">
            <div class="sidebar-title">Quy trình</div>
            <div class="sidebar-text">
                PDF → Chunking → Embedding → ChromaDB → Retrieval → LLM Answer
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
            <div class="brand-title">RAG Assistant</div>
            <div class="brand-subtitle">PDF Question Answering System</div>
        </div>
        <div class="nav-menu">
            <div>Upload</div>
            <div>Pipeline</div>
            <div>Chatbot</div>
            <div>Report</div>
            <div class="nav-button">Bắt đầu</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# HERO SECTION
# =========================
left, right = st.columns([1.05, 0.95], gap="large")

with left:
    st.markdown(
        """
        <div class="hero-label">Ứng dụng RAG cho tài liệu PDF</div>
        <div class="hero-title">
            Hỏi đáp tài liệu rõ ràng hơn <span>trước khi ra quyết định</span>
        </div>
        <div class="hero-desc">
            Tải lên tài liệu PDF, đặt câu hỏi và nhận câu trả lời dựa trên nội dung thật trong tài liệu.
            Hệ thống sử dụng RAG Pipeline để tìm đoạn liên quan trước khi tạo câu trả lời.
        </div>
        <div class="hero-actions">
            <div class="btn-main">Tải PDF lên →</div>
            <div class="btn-dark">Xem quy trình</div>
        </div>
        """,
        unsafe_allow_html=True
    )

with right:
    st.markdown(
        """
        <div class="preview-card">
            <div class="preview-inner">
                <div class="preview-small">Document Intelligence</div>
                <div class="preview-title">Trợ lý đọc hiểu PDF bằng AI</div>
                <div class="preview-text">
                    Phù hợp cho tài liệu học tập, báo cáo, hợp đồng, giáo trình, quy trình nội bộ và tài liệu nghiên cứu.
                </div>
                <div class="preview-step">1. Đọc nội dung PDF</div>
                <div class="preview-step">2. Tìm đoạn liên quan</div>
                <div class="preview-step">3. Trả lời dựa trên tài liệu</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# STATS
# =========================
st.markdown(
    """
    <div class="stats-row">
        <div class="stat-card">
            <div class="stat-number">01</div>
            <div class="stat-label">Tài liệu PDF được xử lý</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">03</div>
            <div class="stat-label">Đoạn context mặc định</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">06</div>
            <div class="stat-label">Bước trong RAG pipeline</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# PIPELINE
# =========================
st.markdown(
    """
    <div class="section-card">
        <div class="section-title">Quy trình xử lý tài liệu</div>
        <div class="section-text">
            Hệ thống không trả lời trực tiếp theo trí nhớ của mô hình. 
            Thay vào đó, tài liệu được chia nhỏ, chuyển thành vector, lưu vào cơ sở dữ liệu 
            và truy xuất lại khi có câu hỏi.
        </div>

        <div class="pipeline-grid">
            <div class="pipeline-item">
                <div class="pipeline-num">1</div>
                <div class="pipeline-title">PDF</div>
                <div class="pipeline-desc">Người dùng tải file PDF lên hệ thống.</div>
            </div>
            <div class="pipeline-item">
                <div class="pipeline-num">2</div>
                <div class="pipeline-title">Chunking</div>
                <div class="pipeline-desc">Văn bản được chia thành nhiều đoạn nhỏ có overlap.</div>
            </div>
            <div class="pipeline-item">
                <div class="pipeline-num">3</div>
                <div class="pipeline-title">Embedding</div>
                <div class="pipeline-desc">Mỗi đoạn được chuyển thành vector số.</div>
            </div>
            <div class="pipeline-item">
                <div class="pipeline-num">4</div>
                <div class="pipeline-title">Retrieval</div>
                <div class="pipeline-desc">Hệ thống tìm các đoạn gần nhất với câu hỏi.</div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# UPLOAD
# =========================
st.markdown("## Tải tài liệu PDF")

uploaded_file = st.file_uploader(
    "Chọn file PDF",
    type=["pdf"]
)

if uploaded_file is not None:
    if st.session_state.pdf_name != uploaded_file.name:
        st.session_state.collection = None
        st.session_state.messages = []

    if st.session_state.collection is None:
        with st.spinner("Đang xử lý tài liệu PDF..."):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(uploaded_file.read())
                temp_path = temp_file.name

            text = read_pdf(temp_path)
            chunks = chunk_text(text)
            collection = create_vector_db(chunks)

            st.session_state.collection = collection
            st.session_state.pdf_name = uploaded_file.name

        st.success(f"Đã xử lý thành công tài liệu: {uploaded_file.name}")

if st.session_state.pdf_name:
    st.markdown(
        f"""
        <div class="section-card">
            <div class="section-title">Tài liệu đang sử dụng</div>
            <div class="section-text">{st.session_state.pdf_name}</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# =========================
# CHAT
# =========================
st.markdown("## Hỏi đáp với tài liệu")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


question = st.chat_input("Nhập câu hỏi của bạn về tài liệu...")

if question:
    st.session_state.messages.append(
        {"role": "user", "content": question}
    )

    with st.chat_message("user"):
        st.write(question)

    if st.session_state.collection is None:
        answer = "Bạn cần tải tài liệu PDF lên trước khi đặt câu hỏi."
    else:
        with st.spinner("Đang tìm thông tin trong tài liệu và tạo câu trả lời..."):
            retrieved_chunks = retrieve_chunks(
                st.session_state.collection,
                question,
                n_results=n_results
            )

            answer = generate_answer(question, retrieved_chunks)

    st.session_state.messages.append(
        {"role": "assistant", "content": answer}
    )

    with st.chat_message("assistant"):
        st.write(answer)


st.markdown(
    """
    <div class="footer">
        RAG PDF Assistant · Built with Streamlit, ChromaDB and Ollama
    </div>
    """,
    unsafe_allow_html=True
)