import re
from difflib import SequenceMatcher
from typing import Optional, Tuple

import fitz

from .pdf_utils import (
    ROMAN_RE,
    SECTION_ID_RE,
    block_rect,
    clean_text_display,
    extract_block_text,
    is_footer_or_header,
    is_toc_page,
    norm,
    same_section_id,
)


# Module này phụ trách nhận diện heading và tìm vùng section trong PDF.

def strip_heading_number(title: str) -> str:
    t = str(title or "").strip()
    t = re.sub(rf"^\s*{SECTION_ID_RE}\.\s*", "", t, flags=re.I)
    return norm(t)


def parse_section_id_from_text(text: str) -> str:
    t = re.sub(r"\s+", " ", str(text or "").strip())
    m = re.match(rf"^\s*(({ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\.\s*(?:\S|$)", t, flags=re.I)
    return m.group(1) if m else ""


def looks_like_heading(text: str) -> bool:
    raw = str(text or "").strip()
    if not raw:
        return False
    joined = re.sub(r"\s+", " ", raw)
    if len(joined) > 180:
        return False
    sid = parse_section_id_from_text(joined)
    if not sid:
        return False
    rest = re.sub(rf"^\s*(({ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\.\s*", "", joined, flags=re.I).strip()
    if not rest:
        return False
    # Không nhận nhầm code line.
    if sid.isdigit() and re.search(r"\b(def|return|for|if|else|print|import)\b", rest):
        return False
    return True


def split_query_section(query: str) -> Tuple[str, str]:
    q = str(query or "").strip()
    m = re.match(rf"^\s*(({ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\.\s+(.+?)\s*$", q, flags=re.I)
    if m:
        return m.group(1).strip(), m.group(3).strip()
    return "", q


def roman_to_int(s: str) -> int:
    s = str(s or "").upper()
    vals = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}
    total = 0
    prev = 0
    for ch in reversed(s):
        v = vals.get(ch, 0)
        if v < prev:
            total -= v
        else:
            total += v
            prev = v
    return total


def section_id_to_nums(sec_id: str):
    sec_id = str(sec_id or "").strip().strip(".")
    if not sec_id:
        return []
    parts = sec_id.split(".")
    out = []
    for idx, part in enumerate(parts):
        if idx == 0 and re.fullmatch(ROMAN_RE, part, flags=re.I):
            out.append(roman_to_int(part))
        elif part.isdigit():
            out.append(int(part))
        else:
            return []
    return out


def fuzzy_title_match(a: str, b: str) -> bool:
    a = norm(a)
    b = norm(b)
    if not a or not b:
        return False
    if a in b or b in a:
        return True
    return SequenceMatcher(None, a, b).ratio() >= 0.72


def should_end_section(current_sec: str, found_sec: str) -> bool:
    """
    Heading mới có phải điểm kết thúc mục hiện tại không.

    Fix V51:
    - Hỏi 4. Giả mã thì các dòng giả mã 1., 2., 3. bên trong KHÔNG làm dừng.
    - Nhưng gặp 5. Cài đặt Python thì dừng.
    """
    current = section_id_to_nums(current_sec)
    found = section_id_to_nums(found_sec)

    if not current or not found:
        return False
    if current == found:
        return False

    # Mục cha: IV gặp IV.1 thì dừng phần intro của IV.
    if len(found) > len(current) and found[:len(current)] == current:
        return True

    # Cùng cấp hoặc cấp cao hơn: thấy mục sau thì dừng.
    min_len = min(len(current), len(found))
    for i in range(min_len):
        if found[i] > current[i]:
            return True
        if found[i] < current[i]:
            return False

    return False


def find_section_range(pdf_path: str, query: str) -> Optional[dict]:
    doc = fitz.open(pdf_path)
    q_sec, q_title = split_query_section(query)
    q_title_norm = strip_heading_number(query)

    found = None
    for page_index in range(len(doc)):
        page = doc[page_index]
        page_text = page.get_text("text") or ""
        if is_toc_page(page_text):
            continue

        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            text = extract_block_text(block)
            if not text or is_footer_or_header(text) or not looks_like_heading(text):
                continue

            heading_sec = parse_section_id_from_text(text)
            heading_title = strip_heading_number(text)

            if q_sec:
                # Ưu tiên số mục. Nếu người dùng gõ "4. Giá mã" nhưng file là "4. Giả mã",
                # vẫn tìm đúng vì số mục 4 đã khớp.
                if same_section_id(heading_sec, q_sec):
                    found = {
                        "start_page": page_index,
                        "start_y": block_rect(block).y0,
                        "title": clean_text_display(text).replace("\n", " "),
                    }
                    break
            else:
                if q_title_norm and fuzzy_title_match(q_title_norm, heading_title):
                    found = {
                        "start_page": page_index,
                        "start_y": block_rect(block).y0,
                        "title": clean_text_display(text).replace("\n", " "),
                    }
                    break
        if found:
            break

    if not found:
        doc.close()
        return None

    for page_index in range(found["start_page"], len(doc)):
        page = doc[page_index]
        page_text = page.get_text("text") or ""
        if page_index != found["start_page"] and is_toc_page(page_text):
            continue

        for block in page.get_text("dict").get("blocks", []):
            if block.get("type") != 0:
                continue
            text = extract_block_text(block)
            if not text or is_footer_or_header(text):
                continue
            y0 = block_rect(block).y0
            if page_index == found["start_page"] and y0 <= found["start_y"] + 3:
                continue
            if looks_like_heading(text):
                current_sec = parse_section_id_from_text(found.get("title", ""))
                next_sec = parse_section_id_from_text(text)
                if should_end_section(current_sec, next_sec):
                    doc.close()
                    return {**found, "end_page": page_index, "end_y": y0}

    doc.close()
    return {**found, "end_page": len(doc) - 1, "end_y": None}


def section_id_from_title_or_query(text: str) -> str:
    sec, _title = split_query_section(text)
    if sec:
        return sec
    return parse_section_id_from_text(text)


def should_stop_at_heading(text: str, current_sec: str) -> bool:
    """
    Strict stop lớp 2.

    Fix V51:
    Không dừng nhầm ở các dòng giả mã/danh sách như:
    1. Đặt left...
    2. Trong khi...
    khi người dùng đang hỏi mục 4. Giả mã.
    Chỉ dừng khi heading mới thật sự là mục kế tiếp, ví dụ 5. Cài đặt Python.
    """
    if not current_sec:
        return False
    if not looks_like_heading(text):
        return False
    found = parse_section_id_from_text(text)
    if not found:
        return False
    return should_end_section(current_sec, found)
