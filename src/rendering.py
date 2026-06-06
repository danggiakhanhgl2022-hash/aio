
import html
from pathlib import Path

import streamlit as st

from .config import SHOW_COPY_TEXT


def render_text_block(text: str):
    text_html = html.escape(text).replace("\n", "<br>")
    st.markdown(
        f"""
<div class="kb-text-block">
{text_html}
</div>
""",
        unsafe_allow_html=True,
    )


def render_image_block(path: str, caption: str = ""):
    if path and Path(path).exists():
        st.image(path, use_container_width=True)
    # Không lặp caption quá nhiều ở dưới ảnh; chỉ hiện nhẹ nếu cần.
    if caption:
        st.markdown(
            f"<div class='kb-caption'>{html.escape(caption)}</div>",
            unsafe_allow_html=True,
        )


def render_interleaved_result(result: dict):
    if not result:
        st.error("Không tìm thấy nội dung phù hợp trong tài liệu.")
        return

    blocks = result.get("blocks", [])
    if not blocks:
        st.warning("Tìm thấy mục nhưng chưa tách được block nội dung.")
        return

    for block in blocks:
        if block.get("type") == "text":
            render_text_block(block.get("text", ""))
        elif block.get("type") == "image":
            render_image_block(block.get("image_path", ""), block.get("caption", ""))

    if SHOW_COPY_TEXT and result.get("copy_text"):
        with st.expander("Mở text trích xuất để copy"):
            st.text_area("Text", result.get("copy_text", ""), height=280, label_visibility="collapsed")
