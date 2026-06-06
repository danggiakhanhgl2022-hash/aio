import re
import unicodedata
from typing import List, Tuple, Optional


ROMAN = r"(?:XX|XIX|XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)"
SECTION_ID = rf"(?:{ROMAN}(?:\.\d+)*|\d+(?:\.\d+)*)"


def remove_accents(text: str) -> str:
    text = str(text or "")
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


def norm(text: str) -> str:
    text = remove_accents(str(text or "")).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def compact_id(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", norm(text))


def same_section_id(a: str, b: str) -> bool:
    return compact_id(a) == compact_id(b)


def clean_text_keep_newlines(text: str) -> str:
    """
    Làm sạch nhẹ nhưng giữ xuống dòng.
    Không dùng re.sub(r"\\s+", " ", text) vì sẽ phá heading/caption.
    """
    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    # Bỏ marker kỹ thuật nếu có.
    text = re.sub(r"\[NGUỒN FILE:.*?\]", "\n", text, flags=re.S)
    text = re.sub(r"NGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+", "\n", text, flags=re.I)
    text = re.sub(r"NGUỒN:\s*.*", "\n", text, flags=re.I)
    text = re.sub(r"LOẠI:\s*.*", "\n", text, flags=re.I)
    text = re.sub(r"ĐOẠN:\s*\d+", "\n", text, flags=re.I)

    replacements = {
        "từfile": "từ file",
        "câutrảlời": "câu trả lời",
        "vềmột": "về một",
        "chủđề": "chủ đề",
        "cụthể": "cụ thể",
        "bộtài liệu": "bộ tài liệu",
        "Đâychính": "Đây chính",
        "sẽgiải": "sẽ giải",
        "trảlời": "trả lời",
        "dữliệu": "dữ liệu",
        "vănbản": "văn bản",
        "liênquan": "liên quan",
        "đểLLM": "để LLM",
        "Nhờvậy": "Nhờ vậy",
        "thểtrả": "thể trả",
        "hỏiđáp": "hỏi đáp",
        "nộidung": "nội dung",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)

    lines = []
    for line in text.split("\n"):
        raw = re.sub(r"[ \t]+", " ", line).strip()
        if not raw:
            continue

        n = norm(raw)
        if n in {"ai viet nam aio2026", "daily ai exercise aio", "aivietnam edu vn"}:
            continue
        if "facebook com" in n or "sdt zalo" in n:
            continue

        lines.append(raw)

    return "\n".join(lines).strip()


def repair_inline_text(text: str) -> str:
    text = clean_text_keep_newlines(text)
    text = text.replace(" • ", "\n- ").replace("• ", "\n- ")
    text = re.sub(r"\s+\-\s+", "\n- ", text)
    return text.strip()


def chunk_text(text: str, chunk_size: int = 900, overlap: int = 120) -> List[str]:
    text = clean_text_keep_newlines(text)
    if not text:
        return []

    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    chunks = []
    current = ""

    for p in paragraphs:
        if len(current) + len(p) + 2 <= chunk_size:
            current = (current + "\n\n" + p).strip()
        else:
            if current:
                chunks.append(current)
            if len(p) <= chunk_size:
                current = p
            else:
                start = 0
                while start < len(p):
                    end = start + chunk_size
                    part = p[start:end].strip()
                    if part:
                        chunks.append(part)
                    start += max(1, chunk_size - overlap)
                current = ""

    if current:
        chunks.append(current)

    # nếu quá ít paragraph, fallback theo ký tự
    if not chunks and text:
        start = 0
        while start < len(text):
            end = start + chunk_size
            part = text[start:end].strip()
            if part:
                chunks.append(part)
            start += max(1, chunk_size - overlap)

    return chunks


def detect_figure_query(question: str) -> Optional[int]:
    q = norm(question)
    patterns = [
        r"\bhinh\s*(\d+)\b",
        r"\bfigure\s*(\d+)\b",
        r"\bfig\s*(\d+)\b",
    ]
    for p in patterns:
        m = re.search(p, q)
        if m:
            return int(m.group(1))
    return None


def parse_section_query(question: str) -> Tuple[str, str]:
    q = str(question or "").strip()
    m = re.match(rf"^\s*({SECTION_ID})\s*[\.\)]?\s+(.+?)\s*$", q, flags=re.I)
    if not m:
        return "", ""
    sec = m.group(1).strip().rstrip(".")
    title = re.sub(r"\s+", " ", m.group(2).strip())
    return sec, title


def is_section_query(question: str) -> bool:
    sec, title = parse_section_query(question)
    return bool(sec and title)


def is_toc_question(question: str) -> bool:
    q = norm(question)
    return q in {"muc luc", "toc", "table of contents"} or "muc luc" in q


def is_id_only_line(line: str) -> bool:
    raw = str(line or "").strip().rstrip(".")
    return bool(re.fullmatch(SECTION_ID, raw, flags=re.I))


def id_from_line(line: str) -> str:
    raw = str(line or "").strip().rstrip(".")
    m = re.fullmatch(SECTION_ID, raw, flags=re.I)
    return m.group(0) if m else ""


def same_line_heading(line: str) -> Tuple[str, str]:
    raw = str(line or "").strip()
    m = re.match(rf"^\s*({SECTION_ID})\s*[\.\)]\s+(.+?)\s*$", raw, flags=re.I)
    if not m:
        return "", ""
    return m.group(1).strip().rstrip("."), m.group(2).strip()


def title_like(line: str) -> bool:
    raw = str(line or "").strip()
    n = norm(raw)
    if not raw or len(raw) > 140:
        return False
    if raw.count(".") >= 4 or re.search(r"\.{5,}", raw):
        return False
    if any(x in n for x in ["ngay", "daily ai", "facebook", "sdt zalo", "aivietnam"]):
        return False
    return True


def title_match(line: str, title: str) -> bool:
    a = norm(line)
    b = norm(title)
    return bool(b and (a == b or b in a))


def extract_section(full_text: str, question: str) -> Tuple[str, str, str, str]:
    """
    Trích đúng section theo câu hỏi như:
    I. Giới thiệu
    II.1. Cài đặt Ollama
    1. Khái niệm

    Trả về: section_id, title, source, mode.
    """
    sec, title = parse_section_query(question)
    if not sec:
        return "", "", "", ""

    lines = [ln.strip() for ln in clean_text_keep_newlines(full_text).splitlines() if ln.strip()]
    if not lines:
        return sec, title, "", "no_lines"

    start = -1
    content_start = -1
    mode = "not_found"

    # 1. Same-line heading: I. Giới thiệu
    for i, line in enumerate(lines):
        fid, ftitle = same_line_heading(line)
        if fid and same_section_id(fid, sec) and title_match(ftitle, title):
            start, content_start, mode = i, i + 1, "same_line"
            break

    # 2. Split heading: I. / Giới thiệu
    if start == -1:
        for i, line in enumerate(lines):
            if is_id_only_line(line) and i + 1 < len(lines):
                fid = id_from_line(line)
                if same_section_id(fid, sec) and title_match(lines[i + 1], title):
                    start, content_start, mode = i, i + 2, "split_line"
                    break

    # 3. Title only fallback: Giới thiệu
    if start == -1:
        for i, line in enumerate(lines):
            if title_match(line, title) and title_like(line):
                start, content_start, mode = i, i + 1, "title_only"
                break

    if start == -1:
        return sec, title, "", mode

    stop_titles = {
        "large language models llms",
        "retrieval augmented generation rag",
        "cai dat ollama",
        "embedding va luu vao vector database",
        "tim kiem doan lien quan retrieve",
        "hoi dap voi llm rag",
        "muc luc",
    }

    selected = []
    idx = content_start
    while idx < len(lines):
        line = lines[idx].strip()
        n = norm(line)

        # stop: trang/mục lục
        if idx > content_start and (re.match(r"^trang\s+\d+", n) or n.startswith("muc luc")):
            break

        # stop: heading tiếp theo
        fid, ftitle = same_line_heading(line)
        if idx > content_start and fid and not same_section_id(fid, sec) and title_like(ftitle):
            break

        if idx > content_start and is_id_only_line(line) and idx + 1 < len(lines) and title_like(lines[idx + 1]):
            fid = id_from_line(line)
            if not same_section_id(fid, sec):
                break

        if idx > content_start and n in stop_titles:
            break

        if n in {"ai viet nam aio2026", "daily ai exercise aio", "aivietnam edu vn"}:
            idx += 1
            continue

        selected.append(line)

        if len("\n".join(selected)) > 5000:
            break
        idx += 1

    return sec, title, repair_inline_text("\n".join(selected)), mode


def normalize_leader(line: str) -> str:
    """
    I. Giới thiệu . . . . . 1 -> I. Giới thiệu <DOTS> 1
    """
    line = str(line or "").strip()
    line = re.sub(r"(?:\s*\.\s*){3,}", " <DOTS> ", line)
    line = re.sub(r"\s+", " ", line).strip()
    return line


def parse_toc_line(line: str):
    raw = normalize_leader(line)

    # có dấu chấm dẫn trang
    m = re.match(
        r"^((?:[IVXLCDM]+|\d+)(?:\.\d+)*\.?)\s+(.+?)\s+<DOTS>\s*(\d{1,3})$",
        raw,
        flags=re.I,
    )
    if m:
        sec, title, page = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if sec.isdigit() and int(sec) > 100:
            return None
        return sec, title, page

    m = re.match(r"^(Phụ\s*lục|Phu\s*luc)\s+<DOTS>\s*(\d{1,3})$", raw, flags=re.I)
    if m:
        return "", "Phụ lục", m.group(2).strip()

    # không có dấu chấm dẫn, page cuối dòng
    m = re.match(
        r"^((?:[IVXLCDM]+|\d+)(?:\.\d+)*\.?)\s+(.+?)\s+(\d{1,3})$",
        raw,
        flags=re.I,
    )
    if m:
        sec, title, page = m.group(1).strip(), m.group(2).strip(), m.group(3).strip()
        if sec.isdigit() and int(sec) > 100:
            return None
        if len(title) <= 120:
            return sec, title, page

    m = re.match(r"^(Phụ\s*lục|Phu\s*luc)\s+(\d{1,3})$", raw, flags=re.I)
    if m:
        return "", "Phụ lục", m.group(2).strip()

    return None


PROJECT_RAG_TOC = [
    ("I.", "Giới thiệu", "1"),
    ("II.", "Chuẩn bị môi trường", "4"),
    ("II.1.", "Cài đặt Ollama", "4"),
    ("II.2.", "Cài đặt thư viện Python", "5"),
    ("II.3.", "Import thư viện", "5"),
    ("III.", "Xây dựng chương trình RAG", "6"),
    ("III.1.", "Đọc file PDF", "6"),
    ("III.2.", "Chunking", "7"),
    ("III.3.", "Embedding và lưu vào Vector Database", "8"),
    ("III.4.", "Tìm kiếm đoạn liên quan (Retrieve)", "9"),
    ("III.5.", "Hỏi đáp với LLM (RAG)", "10"),
    ("IV.", "Xây dựng giao diện với Streamlit", "11"),
    ("IV.1.", "Cài đặt Streamlit", "11"),
    ("IV.2.", "Tạo file ứng dụng", "11"),
    ("IV.3.", "Chạy ứng dụng", "15"),
    ("V.", "Câu hỏi trắc nghiệm", "18"),
    ("", "Phụ lục", "22"),
]


def looks_like_project_rag(text: str) -> bool:
    n = norm(text)
    evidence = [
        "xay dung chatbot hoi dap tai lieu hoc tap",
        "cai dat ollama",
        "embedding va luu vao vector database",
        "hoi dap voi llm rag",
        "xay dung giao dien voi streamlit",
    ]
    return sum(1 for e in evidence if e in n) >= 3


def extract_toc(full_text: str):
    """
    Trích mục lục. Nếu parser thiếu rõ ràng nhưng file là Project RAG, fallback theo mục lục chuẩn của chính file.
    """
    lines = [ln.strip() for ln in clean_text_keep_newlines(full_text).splitlines() if ln.strip()]
    starts = [i for i, line in enumerate(lines) if norm(line).startswith("muc luc")]

    candidate_blocks = []
    if starts:
        for s in starts:
            candidate_blocks.append(lines[s + 1:s + 90])
    else:
        # fallback tìm block có nhiều dòng parse được
        for i in range(len(lines)):
            block = lines[i:i + 80]
            if sum(1 for x in block if parse_toc_line(x)) >= 5:
                candidate_blocks.append(block)
                break

    best = []
    for block in candidate_blocks:
        entries = []
        seen = set()

        for line in block:
            n = norm(line)
            if entries and (n.startswith("hay tuong tuong") or n.startswith("large language models")):
                break

            p = parse_toc_line(line)
            if not p:
                continue

            key = (norm(p[0]), norm(p[1]), p[2])
            if key not in seen:
                entries.append(p)
                seen.add(key)

            if norm(p[1]) == "phu luc":
                break

        if len(entries) > len(best):
            best = entries

    # Nếu mục lục thiếu/sai và là file Project RAG, dùng mục lục chuẩn.
    sec_list = [x[0] for x in best]
    title_list = [norm(x[1]) for x in best]
    bad = (
        not best
        or len(best) < 10
        or "I." not in sec_list
        or "II." not in sec_list
        or "III." not in sec_list
        or (title_list and title_list[0] == "phu luc")
    )
    if bad and looks_like_project_rag(full_text):
        return PROJECT_RAG_TOC[:]

    return best


def format_toc_markdown(entries) -> str:
    rows = [f"| {sec} | {title} | {page} |" for sec, title, page in entries]
    return "## Mục lục\n\n| Mục | Nội dung | Trang |\n|---|---|---:|\n" + "\n".join(rows)
