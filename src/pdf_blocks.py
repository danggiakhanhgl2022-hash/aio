import re
from typing import List

import fitz

from .pdf_sections import looks_like_heading
from .pdf_utils import (
    block_rect,
    clean_text_display,
    extract_block_text,
    is_footer_or_header,
    norm,
)


# Module này phụ trách phân loại block: text, caption, code line, code box, callout box.

def is_caption_text(text: str) -> bool:
    return bool(re.search(r"\b(Hình|Hinh|Figure|Fig\.?)\s*\d+", str(text), flags=re.I))


def is_bullet_paragraph(text: str) -> bool:
    t = str(text or "").strip()
    return t.startswith("•") or t.startswith("-") or t.startswith("*")


def is_numbered_line(text: str) -> bool:
    # Dòng có số thứ tự trong code box, ví dụ: 1 def retrieve(...), 2 docstring, 5 )
    t = str(text or "").strip()
    return bool(re.match(r"^\d+\b", t))


def is_code_line(text: str) -> bool:
    t = str(text or "").strip()
    if not t:
        return False

    # Bullet giải thích là văn bản thường, không phải code.
    if is_bullet_paragraph(t):
        return False

    # Số dòng trống trong code panel.
    if re.fullmatch(r"\d+", t):
        return True

    # Số dòng code: 1 def..., 2 docstring..., 13 documents=...
    if re.match(r"^\d+\s*(?:[|:]\s*)?\S+", t):
        code_words = [
            "def", "return", "for", "if", "else", "print", "import",
            "client", "collection", "messages", "options", "resp",
            "reader", "full_text", "chunks", "page", "documents",
            "embeddings", "ids", "context", "model", "#", ")", "}", "]",
            "\"\"\"", "res", "query", "n_results", "QUERY"
        ]
        after = re.sub(r"^\d+\s*(?:[|:]\s*)?", "", t).strip()
        if any(after.startswith(w) for w in code_words):
            return True
        # Nếu là dòng đánh số trong vùng code và có ký tự code phổ biến
        if any(sym in after for sym in ["=", "(", ")", "[", "]", "{", "}", ".", ":", "\"", "'"]):
            return True

    # Dòng số trống trong code panel.
    if re.fullmatch(r"\d+", t):
        return True

    markers = [
        "def ", "return ", "for ", "if ", "else:", "print(", "import ",
        "client =", "collection", "ollama.", "chromadb", "PROMPT =", "messages=",
        "options=", "reader =", "full_text =", "chunks =", "page.extract_text"
    ]
    return any(m in t for m in markers)


def is_code_panel_title(text: str) -> bool:
    n = norm(text)
    if len(n) > 90:
        return False
    keys = [
        "ham cat nho van ban",
        "tao embedding va luu vector database",
        "prompt va ham hoi dap rag",
        "cai dat thu vien python",
        "doc noi dung file pdf",
        "tao file ung dung",
        "tim kiem doan lien quan",
        "ham tim doan lien quan",
        "ham tim kiem doan lien quan",
        "ham tim doan lien quan retrieve",
        "retrieve",
        "hoi dap voi llm",
        "chay ung dung",
    ]
    return any(k in n for k in keys)


def is_box_title(text: str) -> bool:
    n = norm(text)
    if len(n) > 90:
        return False
    keys = [
        "embedding la gi",
        "tai sao can overlap",
        "chon chunk size va chunk overlap",
        "chon chunk size",
        "chon chunk_size",
        "file pdf mau",
        "temperature la gi",
        "luu tru lau dai", "luu trulau dai",
        "tim kiem bang vector hoat dong the nao",
    ]
    return any(k in n for k in keys)


def collect_raw_blocks(pdf_path: str, sec: dict) -> List[dict]:
    doc = fitz.open(pdf_path)
    raw = []

    for page_index in range(sec["start_page"], sec["end_page"] + 1):
        page = doc[page_index]
        for block in page.get_text("dict").get("blocks", []):
            r = block_rect(block)
            y0, y1 = r.y0, r.y1

            if page_index == sec["start_page"] and y1 < sec["start_y"]:
                continue
            if sec["end_y"] is not None and page_index == sec["end_page"] and y0 >= sec["end_y"]:
                continue

            item = {
                "page_index": page_index,
                "page": page_index + 1,
                "type": block.get("type"),
                "rect": r,
                "block": block,
            }

            if block.get("type") == 0:
                text = extract_block_text(block)
                if not text or is_footer_or_header(text):
                    continue
                item["text"] = clean_text_display(text)
            elif block.get("type") == 1:
                item["text"] = ""
            else:
                continue

            raw.append(item)

    doc.close()
    raw.sort(key=lambda x: (x["page_index"], x["rect"].y0, x["rect"].x0))
    return raw


def add_text_block(output: list, copy_parts: list, text: str, page: int, merge: bool = True):
    text = clean_text_display(text)
    if not text:
        return
    if merge and output and output[-1]["type"] == "text" and output[-1]["page"] == page:
        output[-1]["text"] += "\n\n" + text
    else:
        output.append({"type": "text", "text": text, "page": page})
    copy_parts.append(text)
