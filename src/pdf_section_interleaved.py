
import re
import html
import unicodedata
from pathlib import Path
from typing import Optional, Tuple, List

import fitz  # PyMuPDF


ROMAN_RE = r"(?:XX|XIX|XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)"
SECTION_ID_RE = rf"(?:{ROMAN_RE}(?:\.\d+)*|\d+(?:\.\d+)*)"


# ============================================================
# Normalize
# ============================================================
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


def strip_heading_number(title: str) -> str:
    t = str(title or "").strip()
    t = re.sub(rf"^\s*{SECTION_ID_RE}\.\s*", "", t, flags=re.I)
    return norm(t)


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


# ============================================================
# PDF block helpers
# ============================================================
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


# ============================================================
# Find section
# ============================================================
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
                if same_section_id(heading_sec, q_sec):
                    if not q_title or norm(q_title) in heading_title or heading_title in norm(q_title):
                        found = {
                            "start_page": page_index,
                            "start_y": block_rect(block).y0,
                            "title": clean_text_display(text).replace("\n", " "),
                        }
                        break
            else:
                if q_title_norm and (q_title_norm in heading_title or heading_title in q_title_norm):
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
                doc.close()
                return {**found, "end_page": page_index, "end_y": y0}

    doc.close()
    return {**found, "end_page": len(doc) - 1, "end_y": None}


# ============================================================
# Classify
# ============================================================
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


def section_id_from_title_or_query(text: str) -> str:
    sec, _title = split_query_section(text)
    if sec:
        return sec
    return parse_section_id_from_text(text)


def should_stop_at_heading(text: str, current_sec: str) -> bool:
    """
    Chặn đọc dư: nếu đang lấy III.2 mà gặp III.3 / IV. / IV.1 thì dừng ngay.
    Đây là lớp bảo vệ thứ hai, kể cả find_section_range bị sai.
    """
    if not current_sec:
        return False
    if not looks_like_heading(text):
        return False
    found = parse_section_id_from_text(text)
    if not found:
        return False
    return not same_section_id(found, current_sec)


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
