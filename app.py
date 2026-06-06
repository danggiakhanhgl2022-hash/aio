import os
import shutil
import tempfile
from pathlib import Path

import streamlit as st

from src.config import APP_VERSION
from src.loader import load_files, NotebookData
from src.qa import answer_question
from src.utils import detect_figure_query


st.set_page_config(
    page_title="Khánh AI Notebook",
    page_icon="🧩",
    layout="wide",
)


CSS = """
<style>
:root {
  --green: #2f7d3f;
  --green-dark: #174c2a;
  --cream: #fbf8ef;
  --border: #e8dfcf;
}
html, body, [class*="css"] {
  font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}
.stApp {
  background: radial-gradient(circle at top left, #fff1f1 0, transparent 28%),
              radial-gradient(circle at top right, #e8fff3 0, transparent 28%),
              #fbf8ef;
}
.sidebar-card {
  border: 1px dashed var(--green);
  border-radius: 18px;
  padding: 18px;
  background: rgba(255,255,255,.55);
}
.hero {
  background: linear-gradient(135deg, #103d22, #2f7d3f);
  color: white;
  padding: 34px;
  border-radius: 28px;
  margin-bottom: 22px;
  box-shadow: 0 20px 60px rgba(30,90,44,.18);
}
.hero h1 {
  font-size: 42px;
  margin: 0 0 10px 0;
}
.status {
  border: 1px solid #b7e2bd;
  background: #effcf0;
  color: #075a1d;
  padding: 18px 22px;
  border-radius: 18px;
  font-weight: 700;
}
.chat-card {
  border: 1px solid var(--border);
  background: rgba(255,255,255,.82);
  border-radius: 22px;
  padding: 20px 24px;
  margin: 16px 0;
  box-shadow: 0 10px 40px rgba(0,0,0,.04);
}
.user-card {
  border-left: 8px solid #ff4d5a;
}
.bot-card {
  border-left: 8px solid #ff9f1c;
}
.source-card {
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px;
  background: rgba(255,255,255,.70);
  margin-bottom: 12px;
}
.small-muted { color: #6b7280; font-size: 13px; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def init_state():
    if "notebook" not in st.session_state:
        st.session_state.notebook = None
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "last_sources" not in st.session_state:
        st.session_state.last_sources = []
    if "work_dir" not in st.session_state:
        st.session_state.work_dir = None


def reset_notebook():
    st.session_state.notebook = None
    st.session_state.messages = []
    st.session_state.last_sources = []
    if st.session_state.work_dir and Path(st.session_state.work_dir).exists():
        shutil.rmtree(st.session_state.work_dir, ignore_errors=True)
    st.session_state.work_dir = None


def save_uploads(uploaded_files, work_dir: Path):
    paths = []
    upload_dir = work_dir / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    for uf in uploaded_files:
        out = upload_dir / uf.name
        out.write_bytes(uf.getbuffer())
        paths.append(out)
    return paths


def build_quick_questions(data: NotebookData):
    questions = []

    if data.figures:
        questions.append("hình 1")

    full = data.full_text.lower()
    if "mục lục" in full or "muc luc" in full:
        questions.append("Mục lục")

    # ưu tiên section phổ biến
    if "giới thiệu" in full:
        questions.append("I. Giới thiệu")
    if "embedding" in full:
        questions.append("III.3. Embedding và lưu vào Vector Database")
    if "large language models" in full:
        questions.append("Large Language Models")

    questions.append("Tóm tắt tài liệu")
    questions.append("Nội dung quan trọng")

    # unique
    out = []
    for q in questions:
        if q not in out:
            out.append(q)
    return out[:5]


def render_message(role: str, content: str):
    klass = "user-card" if role == "user" else "bot-card"
    icon = "👤" if role == "user" else "🤖"
    st.markdown(f"<div class='chat-card {klass}'><b>{icon}</b>", unsafe_allow_html=True)
    st.markdown(content, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


init_state()


with st.sidebar:
    st.markdown("## 📚 Nguồn tài liệu")
    notebook_name = st.text_input("Tên notebook", "Notebook tài liệu mới")

    uploaded = st.file_uploader(
        "Thêm nguồn",
        type=["pdf", "txt", "md"],
        accept_multiple_files=True,
        help="Upload PDF/TXT. PDF có caption Hình 1/Hình 2 sẽ được tách hình riêng.",
    )

    col_a, col_b = st.columns(2)
    with col_a:
        create_clicked = st.button("Tạo notebook", use_container_width=True)
    with col_b:
        if st.button("Xóa", use_container_width=True):
            reset_notebook()
            st.rerun()

    use_vision = st.checkbox("Đọc hình ngay khi upload (chậm)", value=False)
    st.caption("Khuyên để TẮT cho nhanh. Khi hỏi `hình 1`, app mới gọi `llava:latest` để đọc hình.")

    if create_clicked:
        if not uploaded:
            st.warning("Bạn cần upload ít nhất một file.")
        else:
            reset_notebook()
            work_dir = Path(tempfile.mkdtemp(prefix="khanh_ai_"))
            st.session_state.work_dir = str(work_dir)

            with st.spinner("Đang đọc file nhanh, tách text và caption hình..."):
                paths = save_uploads(uploaded, work_dir)
                figure_dir = work_dir / "figures"
                data = load_files(paths, figure_dir=figure_dir, use_vision=use_vision)
                st.session_state.notebook = data
                st.session_state.messages = []

            st.success("Tạo notebook thành công.")
            st.rerun()

    st.divider()

    data = st.session_state.notebook
    st.markdown("## 📌 Danh sách nguồn")
    if not data:
        st.info("Chưa có nguồn tài liệu.")
    else:
        for s in data.sources:
            st.markdown(
                f"""
<div class='source-card'>
<b>{s['name']}</b><br>
<span class='small-muted'>Loại: {s['type']} | Trang: {s.get('pages', 0)} | Chunk: {s.get('chunks', 0)} | Hình: {s.get('figures', 0)}</span>
</div>
""",
                unsafe_allow_html=True,
            )


left, right = st.columns([2.2, 1])

with left:
    st.markdown(
        f"""
<div class="hero">
  <h1>🧩 Khánh AI Notebook</h1>
  <div>Upload nhanh → tách caption hình → hỏi hình nào sẽ hiện ảnh đó ngay trong chat.</div>
  <div style="margin-top:10px; opacity:.85">Đang chạy: <b>{APP_VERSION}</b></div>
</div>
""",
        unsafe_allow_html=True,
    )

    data = st.session_state.notebook

    if not data:
        st.info("Hãy upload tài liệu ở thanh bên trái rồi bấm **Tạo notebook**.")
    else:
        st.markdown(
            f"""
<div class="status">
Notebook đã sẵn sàng · {len(data.sources)} nguồn · {len(data.chunks)} đoạn text · {len(data.figures)} hình/caption
</div>
""",
            unsafe_allow_html=True,
        )

        st.markdown("### Gợi ý hỏi nhanh theo file")
        qs = build_quick_questions(data)
        cols = st.columns(min(5, len(qs)))
        for i, q in enumerate(qs):
            with cols[i % len(cols)]:
                if st.button(q, use_container_width=True, key=f"quick_{i}_{q}"):
                    ans, sources = answer_question(q, data)
                    st.session_state.messages.append(("user", q))
                    st.session_state.messages.append(("assistant", ans))
                    st.session_state.last_sources = sources
                    st.rerun()

        for role, content in st.session_state.messages:
            render_message(role, content)

        with st.form("chat_form", clear_on_submit=True):
            q = st.text_input("Hỏi về văn bản hoặc hình trong tài liệu...", placeholder="Ví dụ: hình 1, Mục lục, I. Giới thiệu, Embedding là gì?")
            submitted = st.form_submit_button("Gửi")
            if submitted and q.strip():
                with st.spinner("Đang trả lời theo nguồn..."):
                    ans, sources = answer_question(q.strip(), data)
                st.session_state.messages.append(("user", q.strip()))
                st.session_state.messages.append(("assistant", ans))
                st.session_state.last_sources = sources
                st.rerun()

with right:
    st.markdown("## 🧾 Nguồn & Debug")

    data = st.session_state.notebook
    if not data:
        st.info("Chưa có dữ liệu.")
    else:
        st.markdown(f"**Version:** `{APP_VERSION}`")
        st.metric("Nguồn", len(data.sources))
        st.metric("Text chunks", len(data.chunks))
        st.metric("Hình/caption", len(data.figures))

        with st.expander("Xem hình đã tách", expanded=False):
            if not data.figures:
                st.caption("Chưa phát hiện hình/caption.")
            for fig in data.figures:
                st.markdown(f"**Hình {fig.figure_id} - Trang {fig.page}**")
                st.caption(fig.caption)
                try:
                    st.image(fig.image_path, use_container_width=True)
                except Exception:
                    pass
                if fig.visible_text:
                    st.caption("Chữ trong hình: " + ", ".join(fig.visible_text))
                if fig.vision_error:
                    st.caption("Vision error: " + fig.vision_error[:200])

        with st.expander("Xem nguồn dùng cho câu trả lời gần nhất", expanded=True):
            if not st.session_state.last_sources:
                st.caption("Chưa có nguồn.")
            for src in st.session_state.last_sources:
                st.markdown(f"**{src.get('title', 'Nguồn')}**")
                if src.get("image_path"):
                    try:
                        st.image(src["image_path"], use_container_width=True)
                    except Exception:
                        pass
                st.text_area(
                    "Nội dung nguồn",
                    src.get("content", ""),
                    height=180,
                    key=f"src_{hash(str(src))}",
                )

        with st.expander("Xem text nguồn", expanded=False):
            st.text_area("Full text preview", data.full_text[:6000], height=320)
