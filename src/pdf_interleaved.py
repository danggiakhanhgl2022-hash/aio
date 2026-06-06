import re
from pathlib import Path
from typing import Optional

import fitz

from .pdf_blocks import (
    add_text_block,
    collect_raw_blocks,
    is_box_title,
    is_caption_text,
    is_code_line,
    is_code_panel_title,
    is_numbered_line,
)
from .pdf_sections import (
    find_section_range,
    looks_like_heading,
    section_id_from_title_or_query,
    should_stop_at_heading,
)
from .pdf_utils import (
    clean_text_display,
    crop_region,
    crop_union,
    extract_block_text,
    block_rect,
    is_toc_page,
    union_rect,
)


# Module này điều phối build output xen kẽ: text -> ảnh/code/box -> text.

def build_interleaved_blocks(pdf_path: str, query: str, image_dir: str, zoom: float = 2.0) -> Optional[dict]:
    sec = find_section_range(pdf_path, query)
    if not sec:
        return None

    image_dir = Path(image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)
    for p in image_dir.glob("*.png"):
        try:
            p.unlink()
        except Exception:
            pass

    raw = collect_raw_blocks(pdf_path, sec)

    # Strict section guard: không cho output ăn sang mục kế tiếp.
    # Ví dụ hỏi III.2 thì gặp III.3 / IV. phải dừng, dù boundary trước đó có sai.
    current_sec = section_id_from_title_or_query(sec.get("title", "")) or section_id_from_title_or_query(query)

    output = []
    copy_parts = []
    skip = set()
    img_id = 0

    def save_crop(page_index: int, rect: fitz.Rect, prefix: str):
        nonlocal img_id
        img_id += 1
        out = image_dir / f"{prefix}_{img_id}_p{page_index+1}.png"
        crop_union(pdf_path, page_index, rect, str(out), zoom=zoom)
        return str(out)

    i = 0
    while i < len(raw):
        if i in skip:
            i += 1
            continue

        item = raw[i]
        page_index = item["page_index"]
        text = item.get("text", "")
        rect = item["rect"]
        btype = item["type"]

        # STRICT STOP:
        # Nếu gặp heading của mục khác sau khi đã có output thì dừng ngay.
        # Tránh trường hợp hỏi III.2 nhưng kéo sang III.3 / IV / IV.1.
        if btype == 0 and output and should_stop_at_heading(text, current_sec):
            break

        # 1) Heading => text
        if btype == 0 and looks_like_heading(text):
            add_text_block(output, copy_parts, text.replace("\n", " "), item["page"], merge=False)
            i += 1
            continue

        # 2) Actual image block => image + caption if right below
        if btype == 1:
            union = fitz.Rect(rect)
            caption = ""
            j = i + 1
            if j < len(raw):
                nxt = raw[j]
                if nxt["type"] == 0 and nxt["page_index"] == page_index and is_caption_text(nxt.get("text", "")):
                    if nxt["rect"].y0 - rect.y1 < 90:
                        union = union_rect(union, nxt["rect"])
                        caption = nxt.get("text", "")
                        skip.add(j)
                        copy_parts.append(caption)
            output.append({"type": "image", "image_path": save_crop(page_index, union, "img"), "page": item["page"], "caption": caption})
            i += 1
            continue

        # Only text block below.
        if btype != 0:
            i += 1
            continue

        # 3) Code panel title => crop title + following code lines as image.
        if is_code_panel_title(text):
            union = fitz.Rect(rect)
            group_text = [text]
            j = i + 1
            included = 0
            while j < len(raw):
                nxt = raw[j]
                if nxt["page_index"] != page_index or nxt["type"] != 0:
                    break
                nt = nxt.get("text", "")
                # include all numbered lines inside code panel
                if is_code_line(nt) or is_numbered_line(nt):
                    union = union_rect(union, nxt["rect"])
                    group_text.append(nt)
                    skip.add(j)
                    included += 1
                    j += 1
                    continue
                # If still inside the code box, include very close left-indented text.
                if included > 0 and nxt["rect"].y0 - union.y1 < 16 and nxt["rect"].x0 < 135 and not is_bullet_paragraph(nt):
                    union = union_rect(union, nxt["rect"])
                    group_text.append(nt)
                    skip.add(j)
                    j += 1
                    continue
                break

            if included >= 1:
                output.append({"type": "image", "image_path": save_crop(page_index, union, "code"), "page": item["page"], "caption": text})
                copy_parts.append("\n".join(group_text))
                i += 1
                continue
            # no code after title => treat as text
            add_text_block(output, copy_parts, text, item["page"])
            i += 1
            continue

        # 4) Code lines without title => group as image.
        if is_code_line(text):
            union = fitz.Rect(rect)
            group_text = [text]
            j = i + 1
            while j < len(raw):
                nxt = raw[j]
                if nxt["page_index"] != page_index or nxt["type"] != 0:
                    break
                nt = nxt.get("text", "")
                if is_code_line(nt) or is_numbered_line(nt):
                    union = union_rect(union, nxt["rect"])
                    group_text.append(nt)
                    skip.add(j)
                    j += 1
                    continue
                break
            output.append({"type": "image", "image_path": save_crop(page_index, union, "code"), "page": item["page"], "caption": ""})
            copy_parts.append("\n".join(group_text))
            i += 1
            continue

        # 5) Callout box title => crop title + body as image.
        if is_box_title(text):
            union = fitz.Rect(rect)
            group_text = [text]
            j = i + 1
            while j < len(raw):
                nxt = raw[j]
                if nxt["page_index"] != page_index or nxt["type"] != 0:
                    break
                nt = nxt.get("text", "")
                gap = nxt["rect"].y0 - union.y1
                if gap > 60 or looks_like_heading(nt) or is_code_panel_title(nt) or is_caption_text(nt):
                    break
                # Body of callout is usually indented under/inside the same box.
                if nxt["rect"].x0 >= 70:
                    union = union_rect(union, nxt["rect"])
                    group_text.append(nt)
                    skip.add(j)
                    j += 1
                    continue
                break

            output.append({"type": "image", "image_path": save_crop(page_index, union, "box"), "page": item["page"], "caption": text})
            copy_parts.append("\n".join(group_text))
            i += 1
            continue

        # 6) Caption text alone should be text, not image.
        if is_caption_text(text):
            add_text_block(output, copy_parts, text, item["page"])
            i += 1
            continue

        # 7) Normal paragraph / bullet => text
        add_text_block(output, copy_parts, text, item["page"])
        i += 1

    return {
        "title": sec["title"],
        "blocks": output,
        "copy_text": "\n\n".join(copy_parts),
        "range": sec,
    }


def extract_toc_as_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    for page_index in range(len(doc)):
        page = doc[page_index]
        text = page.get_text("text") or ""
        if is_toc_page(text):
            doc.close()
            return clean_text_display(text)
    doc.close()
    return "Không tìm thấy mục lục trong file."


def find_figure_by_number(pdf_path: str, fig_no: int, image_dir: str, zoom: float = 2.0) -> Optional[dict]:
    doc = fitz.open(pdf_path)
    image_dir = Path(image_dir)
    image_dir.mkdir(parents=True, exist_ok=True)

    cap_re = re.compile(rf"(Hình|Hinh|Figure|Fig\.?)\s*{fig_no}\s*[:.\-]\s*(.+)", re.I)

    for page_index in range(len(doc)):
        page = doc[page_index]
        blocks = page.get_text("dict").get("blocks", [])
        for block in blocks:
            if block.get("type") != 0:
                continue
            text = extract_block_text(block)
            if not text:
                continue
            if not cap_re.search(text.replace("\n", " ")):
                continue

            cap_rect = block_rect(block)
            caption = clean_text_display(text)
            candidate = fitz.Rect(0, max(0, cap_rect.y0 - 280), page.rect.width, cap_rect.y1 + 20)

            for b2 in blocks:
                if b2.get("type") == 1:
                    r2 = block_rect(b2)
                    if r2.y1 <= cap_rect.y0 + 10 and cap_rect.y0 - r2.y1 < 100:
                        candidate = union_rect(r2, cap_rect)
                        break

            out = image_dir / f"figure_{fig_no}_page_{page_index+1}.png"
            crop_region(page, candidate, str(out), zoom=zoom)
            doc.close()
            return {"figure_id": fig_no, "page": page_index + 1, "caption": caption, "image_path": str(out)}
    doc.close()
    return None
