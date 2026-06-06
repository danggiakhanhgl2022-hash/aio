import re
import unicodedata
from pathlib import Path

import fitz  # PyMuPDF


ROMAN_RE = r"(?=[MDCLXVI])M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3})"
SECTION_ID_RE = rf"(?:{ROMAN_RE}(?:\.\d+)*|\d+(?:\.\d+)*)"


# Module này chứa hàm tiện ích chung: chuẩn hóa text, đọc block, crop ảnh, nhận diện footer/mục lục.

def remove_accents(text: str) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def norm(text: str) -> str:
    text = remove_accents(str(text or "")).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", norm(text))


def same_section_id(a: str, b: str) -> bool:
    return compact(a) == compact(b)


def clean_text_display(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    fixes = {
        "bộfile": "bộ file",
        "có thểvượt": "có thể vượt",
        "độchính": "độ chính",
        "câu trảlời": "câu trả lời",
        "cắt nhỏvăn": "cắt nhỏ văn",
        "ta tựviết": "ta tự viết",
        "nhỏcó": "nhỏ có",
        "độdài": "độ dài",
        "tựtrùng": "tự trùng",
        "Sốchunks": "Số chunks",
        "giữngữcảnh": "giữ ngữ cảnh",
        "ởranh": "ở ranh",
        "từngữ": "từ ngữ",
        "bảnđồ": "bản đồ",
        "giá trị1000": "giá trị 1000",
        "sẽlẫn": "sẽ lẫn",
        "sẽlàm": "sẽ làm",
        "sẽchia": "sẽ chia",
        "mởđầu": "mở đầu",
        "bịcắt": "bị cắt",
        "tất cảchunks": "tất cả chunks",
        "thành một dãy số(gọi": "thành một dãy số (gọi",
        "nhỏvăn": "nhỏ văn",
        "chính xác": "chính xác",
    }
    for a, b in fixes.items():
        text = text.replace(a, b)
    text = text.replace("\x11", "").replace("¶", "").strip()

    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def extract_block_text(block: dict) -> str:
    texts = []
    for line in block.get("lines", []):
        line_text = ""
        for span in line.get("spans", []):
            line_text += span.get("text", "")
        line_text = line_text.strip()
        if line_text:
            texts.append(line_text)
    return "\n".join(texts).strip()


def block_rect(block: dict) -> fitz.Rect:
    return fitz.Rect(block.get("bbox", [0, 0, 0, 0]))


def union_rect(a, b) -> fitz.Rect:
    a = fitz.Rect(a)
    b = fitz.Rect(b)
    return fitz.Rect(min(a.x0, b.x0), min(a.y0, b.y0), max(a.x1, b.x1), max(a.y1, b.y1))


def crop_region(page, rect, out_path: str, zoom: float = 2.0, pad: float = 6):
    r = fitz.Rect(rect)
    pr = page.rect
    r = fitz.Rect(max(pr.x0, r.x0 - pad), max(pr.y0, r.y0 - pad), min(pr.x1, r.x1 + pad), min(pr.y1, r.y1 + pad))
    pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom), clip=r, alpha=False)
    pix.save(out_path)
    return out_path


def crop_union(pdf_path: str, page_index: int, rect: fitz.Rect, out_path: str, zoom: float = 2.0):
    doc = fitz.open(pdf_path)
    page = doc[page_index]
    crop_region(page, rect, out_path, zoom=zoom)
    doc.close()
    return out_path


def is_footer_or_header(text: str) -> bool:
    n = norm(text)
    if not n:
        return True
    if n in {"ai viet nam aio2026", "aivietnam edu vn", "daily ai exercise aio"}:
        return True
    if "sdt zalo" in n:
        return True
    if re.fullmatch(r"trang\s+\d+", n):
        return True
    if "facebook com" in n:
        return True
    if "ai viet nam aio2026 aivietnam edu vn" in n:
        return True
    return False


def is_toc_page(page_text: str) -> bool:
    """
    Nhận diện trang Mục lục thật.

    Fix V50:
    Bản cũ nhận nhầm trang nội dung có nhiều mục như IV, IV.1, IV.2
    thành Mục lục, nên hỏi IV / IV.2 không tìm thấy.
    Bây giờ chỉ coi là mục lục nếu:
    - có chữ "Mục lục" ở đầu trang; hoặc
    - có nhiều dòng dạng dot leader kết thúc bằng số trang.
    """
    raw = str(page_text or "")
    n = norm(raw)
    head = norm(raw[:500])

    if "muc luc" in head:
        return True

    dot_leader_lines = 0
    for line in raw.splitlines():
        # Mẫu mục lục: "III.2. Chunking ............ 7"
        if re.search(r"(\.\s*){5,}\d+\s*$", line) or re.search(r"\.{5,}\s*\d+\s*$", line):
            dot_leader_lines += 1

    return dot_leader_lines >= 5
