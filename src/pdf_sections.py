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


# ============================================================
# 1. Nhận diện heading / section
# ============================================================
def strip_heading_number(title: str) -> str:
    t = str(title or "").strip()
    t = re.sub(rf"^\s*{SECTION_ID_RE}\.\s*", "", t, flags=re.I)
    return norm(t)


def parse_section_id_from_text(text: str) -> str:
    """
    Lấy mã mục ở đầu heading.
    Ví dụ:
    - III.2. Chunking -> III.2
    - 4. Giả mã -> 4
    """
    t = re.sub(r"\s+", " ", str(text or "").strip())
    m = re.match(rf"^\s*(({ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\.\s*(?:\S|$)", t, flags=re.I)
    return m.group(1) if m else ""


def looks_like_heading(text: str) -> bool:
    """
    Kiểm tra một text block có giống heading không.
    Tránh nhận nhầm dòng code như "1 def ..." thành heading.
    """
    raw = str(text or "").strip()
    if not raw:
        return False

    joined = re.sub(r"\s+", " ", raw)
    if len(joined) > 180:
        return False

    sid = parse_section_id_from_text(joined)
    if not sid:
        return False

    rest = re.sub(
        rf"^\s*(({ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\.\s*",
        "",
        joined,
        flags=re.I,
    ).strip()

    if not rest:
        return False

    # Tránh nhận nhầm dòng code đánh số là heading.
    if sid.isdigit() and re.search(r"\b(def|return|for|if|else|print|import|client|collection)\b", rest):
        return False

    return True


def split_query_section(query: str) -> Tuple[str, str]:
    """
    Tách câu hỏi thành mã mục + tên mục.
    Ví dụ:
    "III.2. Chunking" -> ("III.2", "Chunking")
    "4. Giả mã" -> ("4", "Giả mã")
    """
    q = str(query or "").strip()
    m = re.match(rf"^\s*(({ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\.\s+(.+?)\s*$", q, flags=re.I)
    if m:
        return m.group(1).strip(), m.group(3).strip()
    return "", q


# ============================================================
# 2. So sánh section
# ============================================================
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
    """
    Cho phép tiêu đề gõ hơi lệch.
    Ví dụ "Giá mã" vẫn tìm được "Giả mã".
    """
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

    Ví dụ:
    - Đang ở 4. Giả mã, gặp dòng "1. Đặt left..." thì KHÔNG dừng.
    - Đang ở 4. Giả mã, gặp "5. Cài đặt Python" thì dừng.
    """
    current = section_id_to_nums(current_sec)
    found = section_id_to_nums(found_sec)

    if not current or not found:
        return False
    if current == found:
        return False

    # Nếu đang hỏi mục cha, ví dụ IV, gặp IV.1 thì dừng phần intro của IV.
    if len(found) > len(current) and found[: len(current)] == current:
        return True

    # Cùng cấp hoặc cấp cao hơn: nếu mục sau lớn hơn thì dừng.
    min_len = min(len(current), len(found))
    for i in range(min_len):
        if found[i] > current[i]:
            return True
        if found[i] < current[i]:
            return False

    return False


def section_id_from_title_or_query(text: str) -> str:
    sec, _title = split_query_section(text)
    if sec:
        return sec
    return parse_section_id_from_text(text)


def should_stop_at_heading(text: str, current_sec: str) -> bool:
    """
    Strict stop:
    Khi đang render một mục, nếu gặp heading của mục kế tiếp thì dừng.
    """
    if not current_sec:
        return False
    if not looks_like_heading(text):
        return False

    found = parse_section_id_from_text(text)
    if not found:
        return False

    return should_end_section(current_sec, found)


# ============================================================
# 3. Tìm vùng section trong PDF
# ============================================================
def find_section_range(pdf_path: str, query: str) -> Optional[dict]:
    """
    Tìm điểm bắt đầu và kết thúc của section người dùng hỏi.

    V55 fix:
    - Lấy page_count ngay khi mở doc.
    - Không gọi len(doc) sau doc.close().
    - Không đóng doc giữa chừng rồi tiếp tục dùng doc.
    - Mọi return đều nằm trong try, doc chỉ đóng trong finally.
    """
    doc = fitz.open(pdf_path)
    page_count = len(doc)

    try:
        q_sec, q_title = split_query_section(query)
        q_title_norm = strip_heading_number(query)

        found = None

        # 1) Tìm heading bắt đầu
        for page_index in range(page_count):
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
                    # Ưu tiên số mục.
                    # Ví dụ: người dùng gõ "4. Giá mã", file là "4. Giả mã",
                    # app vẫn tìm đúng vì số 4 khớp.
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
            return None

        # 2) Tìm heading kế tiếp để làm điểm kết thúc
        for page_index in range(found["start_page"], page_count):
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
                        return {**found, "end_page": page_index, "end_y": y0}

        # 3) Nếu đây là section cuối file, kết thúc ở trang cuối.
        return {**found, "end_page": page_count - 1, "end_y": None}

    finally:
        doc.close()
