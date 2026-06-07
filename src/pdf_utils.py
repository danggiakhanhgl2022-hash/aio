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




def fix_vietnamese_spacing(text: str) -> str:
    """
    Sửa lỗi dính chữ do PDF extract không giữ khoảng trắng.

    Ví dụ:
    - vềmột -> về một
    - chủđềphức tạp -> chủ đề phức tạp
    - cụ thểmà -> cụ thể mà
    - toàn bộtài liệu -> toàn bộ tài liệu
    - khảnăng -> khả năng
    - thểtrả -> thể trả
    - luồng xửlý -> luồng xử lý
    """
    text = str(text or "")

    phrase_fixes = {
        "trang vềmột": "trang về một",
        "trangvề": "trang về",
        "vềmột": "về một",
        "chủđềphức": "chủ đề phức",
        "chủđề": "chủ đề",
        "đềphức": "đề phức",
        "cụ thểmà": "cụ thể mà",
        "toàn bộtài liệu": "toàn bộ tài liệu",
        "bộtài": "bộ tài",
        "tàiliệu": "tài liệu",
        "sẽgiải": "sẽ giải",
        "khảnăng": "khả năng",
        "thểtrả": "thể trả",
        "vềtài": "về tài",
        "luồng xửlý": "luồng xử lý",
        "xửlý": "xử lý",

        "kỹthuật": "kỹ thuật",
        "kỹ thuậtgiúp": "kỹ thuật giúp",
        "hạn chếnày": "hạn chế này",
        "hạn chếlớn": "hạn chế lớn",
        "đểLLM": "để LLM",
        "trảlời": "trả lời",
        "câuhỏi": "câu hỏi",
        "câu hỏi liênquan": "câu hỏi liên quan",
        "văn bản liênquan": "văn bản liên quan",
        "liênquan": "liên quan",
        "có thểtrả": "có thể trả",
        "dựatrên": "dựa trên",
        "bài viếtnày": "bài viết này",
        "tài liệuPDF": "tài liệu PDF",
        "cần hỏiđáp": "cần hỏi đáp",
        "hỏiđáp": "hỏi đáp",
        "trả lời dựatrên": "trả lời dựa trên",
        "nhiệm vụcụthể": "nhiệm vụ cụ thể",
        "cụthể": "cụ thể",
        "phân tíchý": "phân tích ý",
        "cửa sổngữcảnh": "cửa sổ ngữ cảnh",
        "ngữcảnh": "ngữ cảnh",
        "sẽxây": "sẽ xây",
        "sẽđóng": "sẽ đóng",
        "sẽdùng": "sẽ dùng",
        "đểthuận": "để thuận",
        "Ởđây": "Ở đây",
        "không cầnbiết": "không cần biết",

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
    }

    for _ in range(3):
        for a, b in phrase_fixes.items():
            text = text.replace(a, b)

    # Chèn khoảng trắng trước các từ viết hoa/kỹ thuật bị dính.
    text = re.sub(
        r"([a-zà-ỹ])(?=(LLMs|LLM|PDF|RAG|AI|HTML|JavaScript|Streamlit|ChromaDB|Ollama|ChatGPT|Gemini)\b)",
        r"\1 ",
        text,
    )

    # Nhóm từ tiếng Việt hay bị dính ở phía sau.
    right_words = [
        "về", "một", "chủ", "đề", "phức", "tạp", "mà", "bộ", "tài", "liệu",
        "giải", "quyết", "khả", "năng", "thể", "trả", "xử", "lý",
        "này", "lớn", "giúp", "hỏi", "đáp", "liên", "quan", "trên", "dưới",
        "vào", "ra", "của", "cho", "với", "trong", "ngoài", "trước", "sau",
        "thành", "nhiều", "ngắn", "cảnh", "cửa", "sổ", "ngữ", "hạn", "chế",
        "chính", "xác", "thuận", "tiện", "biết", "nhiệm", "vụ", "cụ",
        "phân", "tích", "nghĩa", "đồng", "thời", "đảm", "bảo", "đoạn", "nội",
        "dung", "khi", "ghép", "lại", "không", "vượt", "quá", "giới"
    ]

    for w in sorted(set(right_words), key=len, reverse=True):
        pattern = rf"([a-zà-ỹ])({re.escape(w)})(?=\b|[,.!?;:)\]\s])"
        text = re.sub(pattern, rf"\1 \2", text, flags=re.I)

    for _ in range(2):
        for a, b in phrase_fixes.items():
            text = text.replace(a, b)

    text = re.sub(r"\s+([,.!?;:])", r"\1", text)
    text = re.sub(r"([,.!?;:])(?=[^\s\d])", r"\1 ", text)
    text = re.sub(r"[ \t]{2,}", " ", text)

    return text



def clean_text_display(text: str) -> str:
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\x11", "").replace("¶", "").strip()
    text = fix_vietnamese_spacing(text)

    lines = []
    for line in text.split("\n"):
        line = re.sub(r"[ \t]+", " ", line).strip()
        if line:
            line = fix_vietnamese_spacing(line)
            lines.append(line)

    return "\n".join(lines).strip()



def _line_text_from_spans(line: dict) -> str:
    """
    Ghép các span trong một dòng PDF theo tọa độ.

    Lý do:
    Nếu chỉ dùng span["text"] cộng lại, nhiều PDF sẽ bị dính chữ:
    "vềmột", "chủđề", "đểLLM", "trảlời".

    Cách này dùng khoảng cách x0/x1 giữa 2 span để tự thêm khoảng trắng.
    """
    spans = line.get("spans", []) or []
    spans = [s for s in spans if str(s.get("text", ""))]

    if not spans:
        return ""

    spans = sorted(spans, key=lambda s: (s.get("bbox", [0, 0, 0, 0])[1], s.get("bbox", [0, 0, 0, 0])[0]))

    out = []
    prev_x1 = None
    prev_text = ""
    prev_size = 10.0

    for span in spans:
        stext = str(span.get("text", ""))
        if not stext:
            continue

        bbox = span.get("bbox", [0, 0, 0, 0])
        x0 = float(bbox[0])
        x1 = float(bbox[2])
        size = float(span.get("size", prev_size or 10.0))
        gap = 0 if prev_x1 is None else x0 - float(prev_x1)

        if out:
            need_space = False

            if not prev_text.endswith((" ", "\t", "\n")) and not stext.startswith((" ", "\t", "\n")):
                # Không tách trước dấu câu.
                if stext[0] not in ".,;:!?)]}%”’":
                    # Nếu có khoảng cách vật lý giữa span, xem là khoảng trắng.
                    if gap > max(0.3, max(size, prev_size) * 0.02):
                        need_space = True

                    # Nếu span hiện tại bắt đầu bằng chữ hoa/ký hiệu kỹ thuật, thường là từ mới.
                    if stext[0].isupper():
                        need_space = True

            if need_space:
                out.append(" ")

        out.append(stext)
        prev_x1 = x1
        prev_text = stext
        prev_size = size

    line_text = "".join(out)
    line_text = re.sub(r"[ \t]+", " ", line_text)
    return line_text.strip()



def extract_block_text(block: dict) -> str:
    """
    Lấy text từ một PDF block.

    V58:
    Ghép text theo từng line và từng span bằng tọa độ x0/x1.
    Nhờ vậy app giảm lỗi dính chữ trên nhiều file PDF khác nhau,
    không chỉ sửa riêng một tài liệu.
    """
    texts = []

    for line in block.get("lines", []):
        line_text = _line_text_from_spans(line)
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
