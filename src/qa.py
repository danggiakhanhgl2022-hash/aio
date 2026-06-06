from typing import List, Tuple, Optional
import base64
from pathlib import Path

from .config import LLM_MODEL, TOP_K
from .loader import NotebookData, FigureRecord, TextChunk
from .search import retrieve_chunks
from .vision import analyze_image_with_ollama
from .utils import (
    detect_figure_query,
    extract_toc,
    format_toc_markdown,
    extract_section,
    is_toc_question,
    is_section_query,
    repair_inline_text,
)


def ask_ollama(prompt: str) -> str:
    try:
        import ollama
        res = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )
        return res.get("message", {}).get("content", "").strip()
    except Exception as e:
        return f"[LLM ERROR] {e}"


def markdown_list(items) -> str:
    if not items:
        return ""
    return "\n".join(f"- {x}" for x in items if str(x).strip())




def image_to_html(image_path: str, max_width: int = 780) -> str:
    """
    Nhúng ảnh trực tiếp vào câu trả lời chính bằng base64.
    Như vậy hỏi "hình 1" sẽ thấy hình ngay trong khung chat, không chỉ ở sidebar.
    """
    try:
        path = Path(image_path)
        if not path.exists():
            return ""
        data = base64.b64encode(path.read_bytes()).decode("utf-8")
        return (
            f'<div style="margin:14px 0 18px 0;">'
            f'<img src="data:image/png;base64,{data}" '
            f'style="max-width:{max_width}px;width:100%;border:1px solid #e5e0d5;'
            f'border-radius:16px;box-shadow:0 10px 30px rgba(0,0,0,.08);" />'
            f'</div>'
        )
    except Exception:
        return ""


def answer_figure(question: str, data: NotebookData):
    fig_no = detect_figure_query(question)
    if fig_no is None:
        return None, []

    fig: Optional[FigureRecord] = None
    for f in data.figures:
        if f.figure_id == fig_no:
            fig = f
            break

    if not fig:
        return f"## Hình {fig_no}\n\nKhông tìm thấy hình {fig_no} trong tài liệu.", []

    # V31: Lazy vision.
    # Upload notebook sẽ nhanh; chỉ khi người dùng hỏi đúng hình thì mới gọi vision model.
    need_vision = not fig.visible_text and not fig.summary and not fig.vision_error
    if need_vision:
        vision = analyze_image_with_ollama(
            fig.image_path,
            caption=fig.caption,
            nearby_text=fig.nearby_text,
        )
        fig.visible_text = vision.get("visible_text", []) or []
        fig.objects = vision.get("objects", []) or []
        fig.flow = vision.get("flow", []) or []
        fig.summary = vision.get("summary", "") or ""
        fig.vision_error = vision.get("error", "") or ""

    visible_text = fig.visible_text or []
    objects = fig.objects or []
    flow = fig.flow or []

    answer = f"## Hình trong tài liệu\n\n"
    answer += image_to_html(fig.image_path)
    answer += f"- **{fig.caption or f'Hình {fig.figure_id}'}**\n"
    answer += f"- Trang: **{fig.page}**\n\n"

    if visible_text:
        answer += "### Chữ/nhãn nhìn thấy trong hình\n\n"
        answer += markdown_list(visible_text) + "\n\n"

    if objects:
        answer += "### Thành phần trong hình\n\n"
        answer += markdown_list(objects) + "\n\n"

    if flow:
        answer += "### Luồng xử lý\n\n"
        answer += markdown_list(flow) + "\n\n"

    answer += "### Tóm tắt theo tài liệu\n\n"
    if fig.summary:
        answer += f"- {fig.summary.strip()}\n"
    else:
        # Fallback chắc chắn theo caption + nearby text, không bịa.
        answer += f"- {fig.caption or 'Hình này nằm trong tài liệu.'}\n"
        if fig.nearby_text:
            answer += "- Nội dung liên quan quanh hình trong tài liệu:\n"
            for line in fig.nearby_text.splitlines()[:5]:
                line = line.strip()
                if line and line != fig.caption:
                    answer += f"  - {line}\n"

    if not visible_text and not fig.summary and fig.vision_error:
        answer += "\n> Ghi chú: app đã tìm đúng hình/caption nhưng vision model chưa đọc được ảnh. Kiểm tra `ollama pull llava:latest`.\n"

    sources = [
        {
            "title": f"Hình {fig.figure_id} - trang {fig.page}",
            "content": f"{fig.caption}\n\nChữ trong hình: {', '.join(visible_text)}\n\nTóm tắt: {fig.summary}\n\nVision error: {fig.vision_error}",
            "image_path": fig.image_path,
            "kind": "figure",
        }
    ]
    return answer, sources


def answer_toc(question: str, data: NotebookData):
    if not is_toc_question(question):
        return None, []

    entries = extract_toc(data.full_text)
    if not entries:
        return (
            "## Mục lục\n\nMình chưa tách được mục lục từ text PDF. Để tránh trả lời sai, mình không dùng tìm kiếm tự do cho câu này.",
            [],
        )

    answer = format_toc_markdown(entries)
    source_text = "\n".join(f"{sec} {title} {page}".strip() for sec, title, page in entries)
    sources = [{"title": "Mục lục", "content": source_text, "kind": "toc"}]
    return answer, sources


def answer_section(question: str, data: NotebookData):
    if not is_section_query(question):
        return None, []

    sec, title, source, mode = extract_section(data.full_text, question)

    if not source:
        return (
            f"## {sec}. {title}\n\nMình nhận ra đây là câu hỏi theo mục/section, nhưng chưa tách được đúng nội dung của mục này từ text PDF. Để tránh trả lời sai, mình không dùng tìm kiếm tự do cho câu này.",
            [],
        )

    answer = f"## {sec}. {title}\n\n{source}"
    sources = [{"title": f"{sec}. {title}", "content": source, "kind": f"section:{mode}"}]
    return answer, sources


def answer_text(question: str, data: NotebookData):
    retrieved = retrieve_chunks(question, data.chunks, top_k=TOP_K)

    if not retrieved:
        return "Mình không tìm thấy thông tin này trong tài liệu đã upload.", []

    contexts = []
    sources = []

    for score, ch in retrieved:
        contexts.append(f"[Nguồn: {ch.source_name} | Trang {ch.page} | Đoạn {ch.chunk_id}]\n{ch.text}")
        sources.append(
            {
                "title": f"{ch.source_name} - trang {ch.page} - đoạn {ch.chunk_id}",
                "content": ch.text,
                "kind": "text",
                "score": score,
            }
        )

    context_text = "\n\n---\n\n".join(contexts)

    prompt = f"""
Bạn là trợ lý hỏi đáp tài liệu.

QUY TẮC BẮT BUỘC:
- Chỉ dùng thông tin trong NGUỒN.
- Không bịa.
- Nếu nguồn không đủ, nói rõ là không tìm thấy trong tài liệu.
- Trả lời tiếng Việt, sạch, dễ đọc.
- Không đổ nguyên nguồn thô nếu không cần.
- Nếu câu hỏi hỏi khái niệm, giải thích ngắn và đúng trọng tâm.
- Nếu có bullet trong nguồn, trình bày lại bằng bullet.

CÂU HỎI:
{question}

NGUỒN:
{context_text}
"""

    ans = ask_ollama(prompt)
    if ans.startswith("[LLM ERROR]"):
        # fallback không để app chết
        ans = "Mình tìm thấy thông tin liên quan trong tài liệu:\n\n" + "\n\n".join(
            f"- {repair_inline_text(ch.text[:700])}" for _, ch in retrieved[:3]
        )

    return ans, sources


def answer_question(question: str, data: NotebookData):
    """
    Thứ tự ưu tiên để tránh trả lời sai:
    1. Hình 1 / hình 2 -> kho hình riêng
    2. Mục lục -> parser mục lục riêng
    3. Section I. Giới thiệu / III.3... -> extractor section riêng
    4. Câu hỏi text tự do -> retrieve + LLM
    """
    fig_answer, fig_sources = answer_figure(question, data)
    if fig_answer is not None:
        return fig_answer, fig_sources

    toc_answer, toc_sources = answer_toc(question, data)
    if toc_answer is not None:
        return toc_answer, toc_sources

    sec_answer, sec_sources = answer_section(question, data)
    if sec_answer is not None:
        return sec_answer, sec_sources

    return answer_text(question, data)
