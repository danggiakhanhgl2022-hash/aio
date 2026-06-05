import streamlit as st
from datetime import datetime

from src.multimodal_loader import extract_text_from_file
from src.chunking import chunk_text
from src.vector_db import create_vector_db, retrieve_chunks
from src.rag_pipeline import generate_answer
from src.config import N_RESULTS


# =========================
# PAGE CONFIG
# =========================

st.set_page_config(
    page_title="Khánh AI Notebook",
    page_icon="🎋",
    layout="wide"
)


# =========================
# SESSION STATE
# =========================

defaults = {
    "notebook_title": "Notebook tài liệu mới",
    "sources": [],
    "all_chunks": [],
    "collection": None,
    "messages": [],
    "overview": "",
    "suggested_questions": "",
    "study_guide": "",
    "last_retrieved_chunks": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


# =========================
# CSS
# =========================

st.markdown(
    """
    <style>
    .stApp {
        background: #f7f5ef;
        color: #17231c;
    }

    header {
        visibility: hidden;
    }

    .block-container {
        max-width: 1400px;
        padding-top: 1rem;
        padding-bottom: 3rem;
    }

    h1, h2, h3 {
        color: #17231c !important;
        font-weight: 900 !important;
    }

    .topbar {
        background: white;
        border: 1px solid #e5dfd1;
        border-radius: 24px;
        padding: 20px 28px;
        margin-bottom: 22px;
        box-shadow: 0 14px 36px rgba(37, 72, 45, 0.08);
    }

    .brand {
        font-size: 30px;
        font-weight: 950;
        color: #367541;
        margin-bottom: 4px;
    }

    .brand-sub {
        color: #657066;
        font-size: 15px;
    }

    .notebook-hero {
        background: linear-gradient(135deg, #18351f, #367541);
        color: white;
        border-radius: 28px;
        padding: 34px 38px;
        margin-bottom: 22px;
        box-shadow: 0 20px 46px rgba(37, 72, 45, 0.22);
    }

    .notebook-label {
        color: #d9f7d3;
        font-size: 13px;
        font-weight: 900;
        letter-spacing: 2px;
        text-transform: uppercase;
        margin-bottom: 10px;
    }

    .notebook-title {
        font-size: 38px;
        line-height: 1.18;
        font-weight: 950;
        margin-bottom: 12px;
    }

    .notebook-desc {
        font-size: 17px;
        color: #eef8ec;
        line-height: 1.7;
        max-width: 900px;
    }

    .panel {
        background: white;
        border: 1px solid #e5dfd1;
        border-radius: 22px;
        padding: 22px;
        box-shadow: 0 12px 30px rgba(37, 72, 45, 0.07);
        margin-bottom: 18px;
    }

    .source-card {
        background: #fbfaf6;
        border: 1px solid #e5dfd1;
        border-radius: 16px;
        padding: 15px 16px;
        margin-bottom: 12px;
    }

    .source-title {
        font-weight: 900;
        color: #17231c;
        font-size: 15px;
        margin-bottom: 4px;
    }

    .source-meta {
        color: #6c766d;
        font-size: 13px;
        line-height: 1.5;
    }

    .source-snippet {
        background: #f4f7f1;
        border-left: 5px solid #367541;
        border-radius: 14px;
        padding: 14px 16px;
        margin-bottom: 14px;
        font-size: 14px;
        line-height: 1.6;
    }

    .empty-box {
        background: #fff8e4;
        color: #745000;
        border: 1px solid #f1dca3;
        border-radius: 16px;
        padding: 16px 18px;
        font-weight: 700;
        margin-bottom: 16px;
    }

    .success-box {
        background: #e8f6e8;
        color: #176327;
        border: 1px solid #c7e7c7;
        border-radius: 16px;
        padding: 16px 18px;
        font-weight: 700;
        margin-bottom: 16px;
    }

    [data-testid="stFileUploader"] {
        background: white;
        border: 2px dashed #367541;
        border-radius: 18px;
        padding: 20px;
    }

    [data-testid="stChatMessage"] {
        background: white;
        border: 1px solid #e5dfd1;
        border-radius: 18px;
        padding: 16px;
        margin-bottom: 14px;
        box-shadow: 0 8px 22px rgba(37, 72, 45, 0.04);
    }

    .stButton button {
        border-radius: 999px;
        font-weight: 850;
        border: 1px solid #367541;
        color: #367541;
        background: white;
    }

    .stButton button:hover {
        background: #367541;
        color: white;
        border: 1px solid #367541;
    }
    </style>
    """,
    unsafe_allow_html=True
)


# =========================
# HELPERS
# =========================

def reset_notebook():
    st.session_state.sources = []
    st.session_state.all_chunks = []
    st.session_state.collection = None
    st.session_state.messages = []
    st.session_state.overview = ""
    st.session_state.suggested_questions = ""
    st.session_state.study_guide = ""
    st.session_state.last_retrieved_chunks = []


def make_labeled_chunks(file_name, raw_chunks):
    labeled_chunks = []

    for idx, chunk in enumerate(raw_chunks, start=1):
        labeled = f"[NGUỒN: {file_name} | ĐOẠN: {idx}]\n{chunk}"
        labeled_chunks.append(labeled)

    return labeled_chunks


def parse_source_label(chunk):
    if chunk.startswith("[NGUỒN:") and "]" in chunk:
        label = chunk.split("]", 1)[0].replace("[", "").strip()
        content = chunk.split("]", 1)[1].strip()
        return label, content

    return "Nguồn không xác định", chunk


def process_sources(uploaded_files):
    reset_notebook()

    all_labeled_chunks = []
    sources = []

    for uploaded_file in uploaded_files:
        file_type, extracted_text, status_message = extract_text_from_file(uploaded_file)

        if not extracted_text or not extracted_text.strip():
            sources.append(
                {
                    "name": uploaded_file.name,
                    "type": file_type,
                    "status": "Không đọc được nội dung",
                    "characters": 0,
                    "chunks": 0,
                    "text_preview": ""
                }
            )
            continue

        raw_chunks = chunk_text(extracted_text)

        if not raw_chunks:
            sources.append(
                {
                    "name": uploaded_file.name,
                    "type": file_type,
                    "status": "Không tạo được chunk",
                    "characters": len(extracted_text),
                    "chunks": 0,
                    "text_preview": extracted_text[:1500]
                }
            )
            continue

        labeled_chunks = make_labeled_chunks(uploaded_file.name, raw_chunks)
        all_labeled_chunks.extend(labeled_chunks)

        sources.append(
            {
                "name": uploaded_file.name,
                "type": file_type,
                "status": "Đã xử lý",
                "characters": len(extracted_text),
                "chunks": len(raw_chunks),
                "text_preview": extracted_text[:3000],
                "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        )

    if not all_labeled_chunks:
        st.session_state.sources = sources
        st.session_state.all_chunks = []
        st.session_state.collection = None
        return False

    collection = create_vector_db(all_labeled_chunks)

    st.session_state.sources = sources
    st.session_state.all_chunks = all_labeled_chunks
    st.session_state.collection = collection

    return True


def generate_notebook_output(task_name, instruction, max_chunks=12):
    if not st.session_state.all_chunks:
        return "Bạn cần upload tài liệu trước."

    chunks = st.session_state.all_chunks[:max_chunks]

    prompt = f"""
Bạn là trợ lý nghiên cứu tài liệu theo phong cách NotebookLM.

Nhiệm vụ: {task_name}

Chỉ sử dụng nội dung trong các nguồn tài liệu được cung cấp.
Không bịa thêm thông tin ngoài tài liệu.

Yêu cầu:
- Trả lời bằng tiếng Việt.
- Rõ ràng, có cấu trúc.
- Nếu thiếu dữ liệu, hãy nói rõ là tài liệu chưa đủ thông tin.
- Khi có thể, nhắc nguồn theo dạng [NGUỒN: tên file | ĐOẠN: số].

Hướng dẫn cụ thể:
{instruction}
"""

    try:
        return generate_answer(prompt, chunks)
    except Exception as e:
        return f"Không tạo được nội dung do lỗi: {e}"


def answer_question(question):
    if st.session_state.collection is None:
        return "Bạn cần upload tài liệu trước khi đặt câu hỏi.", []

    retrieved_chunks = retrieve_chunks(
        collection=st.session_state.collection,
        question=question,
        n_results=N_RESULTS
    )

    prompt = f"""
Bạn là trợ lý hỏi đáp tài liệu theo phong cách NotebookLM.

Chỉ được trả lời dựa trên các đoạn nguồn được cung cấp.
Không bịa thêm thông tin ngoài tài liệu.

Câu hỏi:
{question}

Yêu cầu trả lời:
- Trả lời bằng tiếng Việt.
- Trả lời trực tiếp vào câu hỏi.
- Nếu có nhiều ý, chia bullet rõ ràng.
- Cuối các ý quan trọng, ghi nguồn theo dạng [NGUỒN: tên file | ĐOẠN: số].
- Nếu không tìm thấy thông tin trong tài liệu, hãy nói:
"Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."
"""

    try:
        answer = generate_answer(prompt, retrieved_chunks)
    except Exception as e:
        answer = f"Lỗi khi tạo câu trả lời: {e}"

    return answer, retrieved_chunks


# =========================
# SIDEBAR: SOURCE PANEL
# =========================

with st.sidebar:
    st.markdown("## 📚 Nguồn tài liệu")

    st.session_state.notebook_title = st.text_input(
        "Tên notebook",
        value=st.session_state.notebook_title
    )

    uploaded_files = st.file_uploader(
        "Thêm nguồn",
        type=[
            "pdf", "txt",
            "png", "jpg", "jpeg", "webp",
            "mp3", "wav", "m4a",
            "mp4", "mov", "avi", "mkv"
        ],
        accept_multiple_files=True
    )

    if st.button("Tạo notebook từ nguồn", use_container_width=True):
        if not uploaded_files:
            st.warning("Vui lòng chọn ít nhất một file.")
        else:
            with st.spinner("Đang đọc nguồn và tạo notebook..."):
                ok = process_sources(uploaded_files)

            if ok:
                st.success("Đã tạo notebook thành công.")
                st.rerun()
            else:
                st.error("Không có nguồn nào đọc được nội dung.")

    if st.button("Xóa notebook hiện tại", use_container_width=True):
        reset_notebook()
        st.rerun()

    st.markdown("---")

    if st.session_state.sources:
        st.markdown("### Danh sách nguồn")

        for source in st.session_state.sources:
            st.markdown(
                f"""
                <div class="source-card">
                    <div class="source-title">📄 {source.get("name", "")}</div>
                    <div class="source-meta">
                        Loại: {source.get("type", "")}<br>
                        Trạng thái: {source.get("status", "")}<br>
                        Chunk: {source.get("chunks", 0)}<br>
                        Ký tự: {source.get("characters", 0)}
                    </div>
                </div>
                """,
                unsafe_allow_html=True
            )
    else:
        st.info("Chưa có nguồn tài liệu.")


# =========================
# TOP BAR
# =========================

st.markdown(
    f"""
    <div class="topbar">
        <div class="brand">🎋 Khánh AI Notebook</div>
        <div class="brand-sub">
            Trợ lý hỏi đáp tài liệu theo phong cách NotebookLM · Upload nguồn · Hỏi đáp · Tóm tắt · Trích dẫn nguồn
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# HERO
# =========================

st.markdown(
    f"""
    <div class="notebook-hero">
        <div class="notebook-label">Notebook workspace</div>
        <div class="notebook-title">{st.session_state.notebook_title}</div>
        <div class="notebook-desc">
            Tải tài liệu vào thanh bên trái, hệ thống sẽ đọc nội dung, chia chunk,
            tạo vector database và trả lời câu hỏi dựa trên chính nguồn đã tải lên.
            Mỗi câu trả lời có thể xem lại các đoạn nguồn được dùng để suy luận.
        </div>
    </div>
    """,
    unsafe_allow_html=True
)


# =========================
# MAIN LAYOUT
# =========================

left_col, right_col = st.columns([2.1, 1])

with left_col:
    tab_chat, tab_sources = st.tabs(["💬 Chat với tài liệu", "📚 Xem nguồn"])

    with tab_chat:
        if st.session_state.collection is None:
            st.markdown(
                """
                <div class="empty-box">
                    Chưa có notebook. Hãy upload tài liệu ở thanh bên trái rồi bấm "Tạo notebook từ nguồn".
                </div>
                """,
                unsafe_allow_html=True
            )

        else:
            st.markdown(
                f"""
                <div class="success-box">
                    Notebook đã sẵn sàng · {len(st.session_state.sources)} nguồn · {len(st.session_state.all_chunks)} đoạn dữ liệu
                </div>
                """,
                unsafe_allow_html=True
            )

        for message in st.session_state.messages:
            with st.chat_message(message["role"]):
                st.write(message["content"])

        question = st.chat_input("Hỏi bất cứ điều gì về các nguồn tài liệu...")

        if question:
            st.session_state.messages.append(
                {
                    "role": "user",
                    "content": question
                }
            )

            with st.chat_message("user"):
                st.write(question)

            with st.spinner("Đang tìm trong nguồn và tạo câu trả lời..."):
                answer, retrieved_chunks = answer_question(question)

            st.session_state.last_retrieved_chunks = retrieved_chunks

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )

            with st.chat_message("assistant"):
                st.write(answer)

        if st.session_state.last_retrieved_chunks:
            with st.expander("Xem nguồn được dùng để trả lời"):
                for idx, chunk in enumerate(st.session_state.last_retrieved_chunks, start=1):
                    label, content = parse_source_label(chunk)

                    st.markdown(
                        f"""
                        <div class="source-snippet">
                            <b>Nguồn {idx}: {label}</b><br><br>
                            {content[:1200]}
                        </div>
                        """,
                        unsafe_allow_html=True
                    )

    with tab_sources:
        st.markdown("## Nguồn trong notebook")

        if not st.session_state.sources:
            st.info("Chưa có nguồn nào.")
        else:
            for source in st.session_state.sources:
                with st.expander(f"📄 {source.get('name', '')}"):
                    st.write(f"**Loại:** {source.get('type', '')}")
                    st.write(f"**Trạng thái:** {source.get('status', '')}")
                    st.write(f"**Số chunk:** {source.get('chunks', 0)}")
                    st.write(f"**Số ký tự:** {source.get('characters', 0)}")

                    st.text_area(
                        "Nội dung xem trước",
                        value=source.get("text_preview", ""),
                        height=260
                    )


with right_col:
    st.markdown("## 🧠 Studio")

    st.markdown(
        """
        <div class="panel">
            <h3>Công cụ nhanh</h3>
            <p>Tạo tóm tắt, câu hỏi gợi ý và hướng dẫn học từ nguồn tài liệu.</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    if st.button("Tạo tổng quan notebook", use_container_width=True):
        with st.spinner("Đang tạo tổng quan..."):
            st.session_state.overview = generate_notebook_output(
                task_name="Tạo tổng quan notebook",
                instruction="""
Tóm tắt toàn bộ notebook thành các phần:
1. Chủ đề chính
2. Các ý quan trọng
3. Những khái niệm cần chú ý
4. Kết luận ngắn
"""
            )

    if st.button("Tạo câu hỏi gợi ý", use_container_width=True):
        with st.spinner("Đang tạo câu hỏi gợi ý..."):
            st.session_state.suggested_questions = generate_notebook_output(
                task_name="Tạo câu hỏi gợi ý",
                instruction="""
Tạo 8 câu hỏi hay mà người dùng nên hỏi dựa trên tài liệu.
Chỉ tạo câu hỏi liên quan đến nội dung trong nguồn.
"""
            )

    if st.button("Tạo study guide", use_container_width=True):
        with st.spinner("Đang tạo study guide..."):
            st.session_state.study_guide = generate_notebook_output(
                task_name="Tạo study guide",
                instruction="""
Tạo study guide để học tài liệu:
1. Mục tiêu học
2. Kiến thức trọng tâm
3. Thuật ngữ quan trọng
4. Câu hỏi ôn tập
5. Gợi ý cách học
"""
            )

    st.markdown("---")

    with st.expander("Tổng quan notebook", expanded=True):
        if st.session_state.overview:
            st.write(st.session_state.overview)
        else:
            st.caption("Chưa tạo tổng quan.")

    with st.expander("Câu hỏi gợi ý", expanded=False):
        if st.session_state.suggested_questions:
            st.write(st.session_state.suggested_questions)
        else:
            st.caption("Chưa tạo câu hỏi gợi ý.")

    with st.expander("Study guide", expanded=False):
        if st.session_state.study_guide:
            st.write(st.session_state.study_guide)
        else:
            st.caption("Chưa tạo study guide.")

    st.markdown("---")

    st.markdown("## 📊 Trạng thái")

    c1, c2 = st.columns(2)

    with c1:
        st.metric("Nguồn", len(st.session_state.sources))

    with c2:
        st.metric("Đoạn", len(st.session_state.all_chunks))

    st.metric("Tin nhắn", len(st.session_state.messages))