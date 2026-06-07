
import shutil
from pathlib import Path

import streamlit as st

from src.config import APP_VERSION, RUNTIME_DIR, PDF_ZOOM
from src.pdf_section_interleaved import (
    build_interleaved_blocks,
    extract_toc_as_text,
    find_figure_by_number,
    norm,
)
from src.rendering import render_interleaved_result, render_image_block, render_text_block


st.set_page_config(page_title="Khánh AI Notebook", page_icon="🧩", layout="wide")

CSS = """
<style>
.stApp {
  background: radial-gradient(circle at top left, #fff4f2 0, transparent 25%),
              radial-gradient(circle at top right, #ebfff3 0, transparent 30%),
              #fbf8ef;
}
section[data-testid="stSidebar"] { background: #f3f6fa; }
.kb-hero {
  background: linear-gradient(135deg, #103d22, #2f7d3f);
  color: white; padding: 28px 32px; border-radius: 24px;
  box-shadow: 0 18px 60px rgba(20,70,40,.16); margin-bottom: 18px;
}
.kb-hero h1 { margin: 0 0 8px 0; font-size: 36px; }
.kb-status {
  border: 1px solid #bfe7c3; background: #effcf0; color: #075a1d;
  padding: 14px 18px; border-radius: 16px; font-weight: 700; margin-bottom: 18px;
}
.kb-chat-card {
  border: 1px solid #e5dbc9; background: rgba(255,255,255,.86);
  border-radius: 22px; padding: 18px 22px; margin: 16px 0;
  box-shadow: 0 10px 38px rgba(0,0,0,.045);
}
.kb-user { border-left: 8px solid #ff4d5a; }
.kb-bot { border-left: 8px solid #ff9f1c; }
.kb-text-block {
  font-size: 1.08rem; line-height: 1.85; margin: 14px 0 18px 0;
}
.kb-caption {
  color: #526071; font-size: .92rem; margin-top: -8px; margin-bottom: 16px;
  text-align: center;
}
/* Ẩn menu/toolbar mặc định của Streamlit để tránh bấm nhầm Clear caches khi copy */
#MainMenu {visibility: hidden !important;}
footer {visibility: hidden !important;}
header [data-testid="stToolbar"] {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
.stDeployButton {display: none !important;}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)


def ensure_state():
    st.session_state.setdefault("pdf_paths", [])
    st.session_state.setdefault("messages", [])
    st.session_state.setdefault("last_result", None)
    st.session_state.setdefault("upload_dir", str(Path(RUNTIME_DIR) / "uploads"))
    st.session_state.setdefault("image_dir", str(Path(RUNTIME_DIR) / "rendered"))


def reset_all():
    st.session_state.pdf_paths = []
    st.session_state.messages = []
    st.session_state.last_result = None
    runtime = Path(RUNTIME_DIR)
    if runtime.exists():
        shutil.rmtree(runtime, ignore_errors=True)
    (runtime / "uploads").mkdir(parents=True, exist_ok=True)
    (runtime / "rendered").mkdir(parents=True, exist_ok=True)


def save_uploads(files):
    upload_dir = Path(st.session_state.upload_dir)
    upload_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for f in files:
        safe_name = f.name.replace("/", "_").replace("\\", "_")
        out = upload_dir / safe_name
        out.write_bytes(f.getbuffer())
        paths.append(str(out))
    return paths


def current_pdf_path():
    return st.session_state.pdf_paths[0] if st.session_state.pdf_paths else ""


def is_toc_query(q: str):
    n = norm(q)
    return n in {"muc luc", "toc", "table of contents"} or "muc luc" in n


def detect_figure_query(q: str):
    import re
    n = norm(q)
    m = re.search(r"\b(?:hinh|figure|fig)\s*(\d+)\b", n)
    return int(m.group(1)) if m else None


def answer_query(q: str):
    pdf = current_pdf_path()
    if not pdf:
        return {"kind": "text", "text": "Bạn cần upload PDF trước."}

    image_dir = Path(st.session_state.image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)

    if is_toc_query(q):
        return {"kind": "text", "text": extract_toc_as_text(pdf)}

    fig_no = detect_figure_query(q)
    if fig_no is not None:
        fig = find_figure_by_number(pdf, fig_no, image_dir=str(image_dir / f"figure_{fig_no}"), zoom=PDF_ZOOM)
        if not fig:
            return {"kind": "text", "text": f"Không tìm thấy hình {fig_no} trong PDF."}
        return {"kind": "figure", "figure": fig}

    safe_query = "".join(ch if ch.isalnum() else "_" for ch in q)[:80]
    result = build_interleaved_blocks(
        pdf_path=pdf,
        query=q,
        image_dir=str(image_dir / safe_query),
        zoom=PDF_ZOOM,
    )
    if result:
        return {"kind": "interleaved", "result": result}

    return {
        "kind": "text",
        "text": "Không tìm thấy đúng mục bạn hỏi. Hãy nhập đúng tiêu đề, ví dụ: `III.2. Chunking` hoặc `Embedding và lưu vào Vector Database`.",
    }


def render_answer(answer):
    kind = answer.get("kind")
    if kind == "text":
        render_text_block(answer.get("text", ""))
    elif kind == "figure":
        fig = answer.get("figure", {})
        st.markdown(f"### Hình {fig.get('figure_id')} - trang {fig.get('page')}")
        render_image_block(fig.get("image_path", ""), fig.get("caption", ""))
    elif kind == "interleaved":
        render_interleaved_result(answer.get("result"))
    else:
        st.write(answer)


def quick_questions():
    return [
        "III.2. Chunking",
        "III.3. Embedding và lưu vào Vector Database",
        "III.4. Tìm kiếm đoạn liên quan (Retrieve)",
        "Mục lục",
        "hình 2",
    ]


ensure_state()
Path(RUNTIME_DIR).mkdir(exist_ok=True)
Path(st.session_state.upload_dir).mkdir(parents=True, exist_ok=True)
Path(st.session_state.image_dir).mkdir(parents=True, exist_ok=True)

with st.sidebar:
    st.markdown("## 📚 Nguồn tài liệu")
    st.text_input("Tên notebook", "Notebook tài liệu mới")
    uploaded = st.file_uploader("Thêm nguồn", type=["pdf"], accept_multiple_files=True)

    col1, col2 = st.columns(2)
    with col1:
        create = st.button("Tạo notebook", use_container_width=True)
    with col2:
        clear = st.button("Xóa", use_container_width=True)

    if clear:
        reset_all()
        st.rerun()

    if create:
        if not uploaded:
            st.warning("Bạn cần upload PDF.")
        else:
            reset_all()
            st.session_state.pdf_paths = save_uploads(uploaded)
            st.success("Đã tạo notebook.")
            st.rerun()

    st.divider()
    st.markdown("## 📌 Danh sách nguồn")
    if not st.session_state.pdf_paths:
        st.info("Chưa có nguồn tài liệu.")
    else:
        for p in st.session_state.pdf_paths:
            st.markdown(f"**{Path(p).name}**")
            st.caption(p)

left, right = st.columns([2.2, 1])

with left:
    st.markdown(
        f"""
<div class="kb-hero">
  <h1>🧩 Khánh AI Notebook</h1>
  <div>Hỏi mục nào → in đúng thứ tự: văn bản → hình/code/box → văn bản.</div>
  <div style="margin-top:10px; opacity:.9">Đang chạy: <b>{APP_VERSION}</b></div>
</div>
""",
        unsafe_allow_html=True,
    )

    if not st.session_state.pdf_paths:
        st.info("Hãy upload PDF bên trái rồi bấm **Tạo notebook**.")
    else:
        st.markdown(f"<div class='kb-status'>Notebook đã sẵn sàng · {len(st.session_state.pdf_paths)} nguồn</div>", unsafe_allow_html=True)

        st.markdown("### Gợi ý hỏi nhanh theo file")
        cols = st.columns(5)
        for i, q in enumerate(quick_questions()):
            with cols[i]:
                if st.button(q, use_container_width=True, key=f"quick_{i}"):
                    ans = answer_query(q)
                    st.session_state.messages.append(("user", q))
                    st.session_state.messages.append(("assistant", ans))
                    st.session_state.last_result = ans
                    st.rerun()

        for role, content in st.session_state.messages:
            if role == "user":
                st.markdown('<div class="kb-chat-card kb-user">👤</div>', unsafe_allow_html=True)
                st.markdown(content)
            else:
                st.markdown('<div class="kb-chat-card kb-bot">🤖</div>', unsafe_allow_html=True)
                render_answer(content)

        with st.form("chat_form", clear_on_submit=True):
            q = st.text_input(
                "Hỏi về văn bản hoặc hình trong tài liệu...",
                placeholder="Ví dụ: Mục lục, 4. Giả mã, hình 1, IV.2. Tạo file ứng dụng",
            )
            submitted = st.form_submit_button("Gửi")
            if submitted and q.strip():
                with st.spinner("Đang đọc đúng vùng PDF..."):
                    ans = answer_query(q.strip())
                st.session_state.messages.append(("user", q.strip()))
                st.session_state.messages.append(("assistant", ans))
                st.session_state.last_result = ans
                st.rerun()

with right:
    st.markdown("## 🧾 Nguồn & Debug")
    st.markdown(f"**Version:** `{APP_VERSION}`")
    pdf = current_pdf_path()
    if pdf:
        st.markdown(f"**PDF:** {Path(pdf).name}")
    else:
        st.info("Chưa có dữ liệu.")

    with st.expander("Kết quả gần nhất", expanded=False):
        st.json(st.session_state.last_result if st.session_state.last_result else {})
