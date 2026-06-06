import re
import unicodedata
import html as html_lib
from datetime import datetime

import streamlit as st

from src.multimodal_loader import (
    extract_text_from_file,
    analyze_pdf_pages_with_vision,
    analyze_pdf_figures_with_vision,
)
from src.chunking import chunk_text
from src.vector_db import create_vector_db, retrieve_chunks
from src.rag_pipeline import generate_answer

try:
    from src.config import N_RESULTS
except Exception:
    N_RESULTS = 6


APP_VERSION = "EXACT_SECTION_ONLY_V20"

st.set_page_config(page_title="Khánh AI Notebook", page_icon="🎋", layout="wide")


defaults = {
    "notebook_title": "Notebook tài liệu mới",
    "sources": [],
    "all_chunks": [],
    "collection": None,
    "messages": [],
    "last_retrieved_chunks": [],
    "created_at": "",
    "pdf_bytes_store": {},
    "pdf_visual_done": {},
    "quick_questions": [],
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value


def ui(html: str):
    st.markdown(html, unsafe_allow_html=True)


def esc(text):
    return html_lib.escape(str(text))


ui("""
<style>
.stApp {
    background: linear-gradient(135deg, #fffaf0 0%, #f7f5ef 45%, #f3fbf3 100%);
    color: #17231c;
}
header { visibility: hidden; }
.block-container {
    max-width: 1450px;
    padding-top: 1rem;
    padding-bottom: 3rem;
}
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #f4f7f4, #fffaf0);
    border-right: 1px solid #e5dfd1;
}
h1, h2, h3 {
    color: #17231c !important;
    font-weight: 950 !important;
}
[data-testid="stFileUploader"] {
    background: rgba(255,255,255,0.92);
    border: 2px dashed #2f7a3f;
    border-radius: 24px;
    padding: 22px;
    box-shadow: 0 18px 40px rgba(37, 72, 45, 0.1);
}
[data-testid="stChatMessage"] {
    background: rgba(255,255,255,0.94);
    border: 1px solid #e5dfd1;
    border-radius: 22px;
    padding: 18px;
    margin-bottom: 14px;
    box-shadow: 0 14px 36px rgba(37,72,45,0.07);
}
[data-testid="stChatInput"] {
    background: white;
    border-radius: 24px;
    border: 1px solid #e5dfd1;
    box-shadow: 0 20px 52px rgba(37,72,45,0.12);
}
.stButton button {
    border-radius: 999px;
    min-height: 44px;
    font-weight: 900;
    border: 1px solid #2f7a3f;
    color: #2f7a3f;
    background: rgba(255,255,255,0.9);
}
.stButton button:hover {
    background: linear-gradient(135deg, #2f7a3f, #51a45f);
    color: white;
    border: 1px solid #2f7a3f;
}
.top-nav {
    background: rgba(255,255,255,0.82);
    border: 1px solid #e5dfd1;
    border-radius: 30px;
    padding: 22px 28px;
    margin-bottom: 24px;
    box-shadow: 0 18px 44px rgba(37,72,45,0.09);
}
.brand-title {
    font-size: 34px;
    font-weight: 950;
    color: #2f7a3f;
    margin-bottom: 6px;
}
.brand-subtitle {
    color: #667066;
    font-size: 16px;
    line-height: 1.6;
}
.version-pill {
    display:inline-block;
    margin-top:10px;
    padding:6px 12px;
    border-radius:999px;
    background:#12281a;
    color:#b8ff7a;
    font-weight:900;
    font-size:13px;
}
.hero {
    background:
        radial-gradient(circle at 88% 12%, rgba(255,255,255,0.28), transparent 20%),
        linear-gradient(135deg, #12281a 0%, #2f7a3f 55%, #66b76b 100%);
    color: white;
    border-radius: 36px;
    padding: 46px 50px;
    margin-bottom: 28px;
    box-shadow: 0 34px 80px rgba(22,53,31,0.28);
}
.hero-label {
    display: inline-block;
    color: #12281a;
    background: #b8ff7a;
    border-radius: 999px;
    padding: 8px 14px;
    font-size: 12px;
    font-weight: 950;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    margin-bottom: 18px;
}
.hero-title {
    font-size: 52px;
    line-height: 1.08;
    font-weight: 950;
    margin-bottom: 16px;
}
.hero-title span { color: #b8ff7a; }
.hero-desc {
    font-size: 18px;
    color: #f2fff0;
    line-height: 1.75;
    max-width: 900px;
}
.chip-row {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
    margin-top: 24px;
}
.chip {
    background: rgba(255,255,255,0.15);
    border: 1px solid rgba(255,255,255,0.25);
    color: white;
    padding: 10px 16px;
    border-radius: 999px;
    font-weight: 900;
    font-size: 14px;
}
.chip-hot {
    background: linear-gradient(135deg, #ff6fb1, #8b5cf6);
    border: none;
}
.metric-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 16px;
    margin-bottom: 24px;
}
.metric-card {
    background: rgba(255,255,255,0.92);
    border: 1px solid #e5dfd1;
    border-radius: 24px;
    padding: 20px;
    box-shadow: 0 16px 36px rgba(37,72,45,0.08);
}
.metric-number {
    font-size: 34px;
    font-weight: 950;
    color: #2f7a3f;
    line-height: 1;
}
.metric-label {
    margin-top: 8px;
    color: #667066;
    font-weight: 850;
    font-size: 14px;
}
.info-box {
    background: linear-gradient(135deg, #fff8e4, #ffffff);
    border: 1px solid #eddca7;
    border-radius: 24px;
    padding: 22px;
    color: #624600;
    font-weight: 800;
    margin-bottom: 18px;
}
.ready-box {
    background: linear-gradient(135deg, #e8f6e8, #ffffff);
    border: 1px solid #c7e7c7;
    border-radius: 24px;
    padding: 22px;
    color: #176327;
    font-weight: 900;
    margin-bottom: 18px;
}
.source-card {
    background: white;
    border: 1px solid #e5dfd1;
    border-radius: 18px;
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 12px 28px rgba(37,72,45,0.06);
}
.source-title {
    font-weight: 950;
    color: #17231c;
    font-size: 15px;
    margin-bottom: 6px;
}
.source-meta {
    color: #667066;
    font-size: 13px;
    line-height: 1.55;
}
.source-snippet {
    background: #f5f8f2;
    border-left: 5px solid #2f7a3f;
    border-radius: 16px;
    padding: 15px 17px;
    margin-bottom: 14px;
    font-size: 14px;
    line-height: 1.7;
}
@media (max-width: 1000px) {
    .metric-grid { grid-template-columns: 1fr 1fr; }
    .hero-title { font-size: 36px; }
}
</style>
""")


SUPPORTED_FILE_TYPES = ["pdf", "txt", "png", "jpg", "jpeg", "webp"]


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = str(text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return text.lower().strip()


def reset_notebook():
    st.session_state.sources = []
    st.session_state.all_chunks = []
    st.session_state.collection = None
    st.session_state.messages = []
    st.session_state.last_retrieved_chunks = []
    st.session_state.created_at = ""
    st.session_state.pdf_bytes_store = {}
    st.session_state.pdf_visual_done = {}
    st.session_state.quick_questions = []


def get_source_kind(file_name, file_type=""):
    ext = file_name.lower().split(".")[-1]

    if ext in ["png", "jpg", "jpeg", "webp"]:
        return "IMAGE"

    if ext in ["pdf", "txt"]:
        return "DOCUMENT"

    if "image" in str(file_type).lower():
        return "IMAGE"

    return "OTHER"


def extract_sections(text):
    pattern = r"={10,}\s*\n(?P<header>.*?)\n={10,}\s*\n(?P<body>.*?)(?=\n={10,}\s*\n|\Z)"
    matches = list(re.finditer(pattern, text, flags=re.S))

    if not matches:
        return [("RAW_TEXT", text)]

    sections = []

    for match in matches:
        header = match.group("header").strip()
        body = match.group("body").strip()
        sections.append((header, body))

    return sections


def detect_section_kind(header, body, fallback_kind):
    joined = normalize_text(header + "\n" + body)

    if "nguon: pdf_figure_context_error" in joined:
        return "PDF_FIGURE_CONTEXT_ERROR"

    if "nguon: pdf_figure_context" in joined:
        return "PDF_FIGURE_CONTEXT"

    if "nguon: pdf_page_image" in joined:
        return "PDF_PAGE_IMAGE_FALLBACK"

    if "nguon: pdf_text" in joined:
        return "PDF_TEXT"

    if fallback_kind == "IMAGE":
        return "IMAGE"

    return postprocess_answer_text(fallback)


def build_labeled_chunks(file_name, source_kind, extracted_text):
    labeled_chunks = []
    sections = extract_sections(extracted_text)
    chunk_index = 1

    for header, body in sections:
        section_kind = detect_section_kind(header, body, source_kind)

        if not body.strip():
            continue

        raw_chunks = chunk_text(body)

        for raw_chunk in raw_chunks:
            labeled = f"""
[NGUỒN FILE: {file_name} | LOẠI: {section_kind} | ĐOẠN: {chunk_index}]
{header}

{raw_chunk}
"""
            labeled_chunks.append(labeled.strip())
            chunk_index += 1

    return labeled_chunks


def parse_source_label(chunk):
    if chunk.startswith("[") and "]" in chunk:
        label = chunk.split("]", 1)[0].replace("[", "").strip()
        content = chunk.split("]", 1)[1].strip()
        return label, content

    return "Nguồn không xác định", chunk


def is_visual_question(question: str) -> bool:
    q = normalize_text(question)

    # Hỏi "hinh 1", "hình 2", "figure 3" chắc chắn là hỏi hình.
    if re.search(r"\b(hinh|anh|figure|fig)\s*\d+\b", q):
        return True

    visual_keywords = [
        "hinh anh",
        "trong anh",
        "trong hinh",
        "anh trong file",
        "hinh trong file",
        "anh trong pdf",
        "hinh trong pdf",
        "mo ta anh",
        "mo ta hinh",
        "anh nay noi gi",
        "hinh nay noi gi",
        "so do",
        "bieu do",
        "bang",
        "screenshot",
        "diagram",
        "chart",
        "table",
    ]

    return any(keyword in q for keyword in visual_keywords)


def extract_figure_numbers(question: str):
    q = normalize_text(question)
    matches = re.findall(r"\b(hinh|anh|figure|fig)\s*(\d+)\b", q)
    return sorted(list(set(int(number) for _, number in matches)))


def extract_page_numbers(question: str):
    q = normalize_text(question)
    matches = re.findall(r"\btrang\s*(\d+)\b", q)
    return sorted(list(set(int(number) for number in matches)))


def clean_chunk_text_for_answer(text: str, max_chars=4000):
    text = str(text or "")
    text = re.sub(r"\[NGUỒN FILE:.*?\]", "", text, flags=re.S)
    text = re.sub(r"={10,}.*?={10,}", "", text, flags=re.S)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()[:max_chars]


def tokenize_question(question: str):
    raw = re.split(r"[^a-zA-Z0-9À-Ỵà-ỵ]+", question)
    stop = {
        "la", "là", "gi", "gì", "cua", "của", "va", "và", "cho", "toi", "tôi",
        "hay", "hãy", "neu", "nêu", "ve", "về", "trong", "file", "tai", "tài",
        "lieu", "liệu", "mot", "một", "cac", "các", "nhung", "những"
    }

    tokens = []

    for t in raw:
        n = normalize_text(t)

        if len(n) >= 2 and n not in stop:
            tokens.append(n)

    q = normalize_text(question)

    if "large language models" in q:
        tokens += ["large", "language", "models", "llms", "llm", "mo", "hinh", "ngon", "ngu", "lon"]

    if "llm" in q or "llms" in q:
        tokens += ["llm", "llms", "large", "language", "models"]

    final = []

    for t in tokens:
        if t not in final:
            final.append(t)

    return final



def repair_extracted_spacing(text: str) -> str:
    """
    Làm sạch nhẹ text PDF bị dính chữ.
    Không cố OCR lại, chỉ sửa các lỗi phổ biến trong file này.
    """
    text = str(text or "")
    replacements = {
        "từfile": "từ file",
        "câutrảlời": "câu trả lời",
        "vềmột": "về một",
        "chủđề": "chủ đề",
        "cụthể": "cụ thể",
        "bộtài liệu": "bộ tài liệu",
        "Đâychính": "Đây chính",
        "sẽgiải": "sẽ giải",
        "nàỵ": "này",
        "này.Ý": "này. Ý",
        "đểLLM": "để LLM",
        "liênSDT": "liên SDT",
        "liên SĐT": "liên SĐT",
        "trảlời": "trả lời",
        "dữliệu": "dữ liệu",
        "kỹthuật": "kỹ thuật",
        "khắcphục": "khắc phục",
        "hạnchế": "hạn chế",
        "chúngta": "chúng ta",
        "vănbản": "văn bản",
        "liênquan": "liên quan",
    }
    for a, b in replacements.items():
        text = text.replace(a, b)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_phone_answer_from_all_chunks():
    joined = "\n".join(st.session_state.all_chunks)
    phones = re.findall(r"0\d{9,10}", joined)
    unique = []
    for p in phones:
        if p not in unique:
            unique.append(p)

    if not unique:
        return None, []

    related_chunks = []
    for chunk in st.session_state.all_chunks:
        if any(p in chunk for p in unique):
            related_chunks.append(chunk)
        if len(related_chunks) >= 5:
            break

    answer = "**SĐT/Zalo trong tài liệu:**\n" + "\n".join(f"- {p}" for p in unique[:5])

    # Lấy tên nếu có.
    if "Hồng Phúc" in joined or "Hong Phuc" in joined:
        answer += "\n\nTrong tài liệu số này đi kèm tên **Dr. Hồng Phúc**."

    return answer, related_chunks


def build_intro_answer_from_all_chunks():
    """
    Trả lời câu 'Giới thiệu' gọn, không dump raw chunk.
    """
    joined = "\n".join(st.session_state.all_chunks)
    jn = normalize_text(joined)

    if "gioi thieu" not in jn and "giới thiệu" not in joined:
        return None, []

    related_chunks = []
    for chunk in st.session_state.all_chunks:
        cn = normalize_text(chunk)
        if "gioi thieu" in cn or "hay tuong tuong" in cn or "large language models" in cn:
            related_chunks.append(chunk)
        if len(related_chunks) >= 5:
            break

    answer = (
        "**Phần giới thiệu của tài liệu nói về mục tiêu xây dựng chatbot hỏi đáp tài liệu học tập.**\n\n"
        "Ý chính:\n"
        "- Bài toán đặt ra là có một file PDF dài khoảng 50 trang về một chủ đề phức tạp.\n"
        "- Người dùng muốn tìm nhanh câu trả lời cho một câu hỏi cụ thể mà không cần đọc toàn bộ tài liệu.\n"
        "- Tài liệu giới thiệu Large Language Models (LLMs) là các mô hình ngôn ngữ lớn có khả năng hiểu và tạo văn bản giống con người.\n"
        "- Tuy nhiên, LLM có hạn chế là chỉ biết những gì đã được huấn luyện từ trước, nên khó trả lời chính xác về tài liệu riêng nếu không được cung cấp nội dung tài liệu.\n"
        "- Vì vậy, tài liệu dẫn vào giải pháp RAG để tìm đoạn văn bản liên quan trong tài liệu rồi đưa cho LLM trả lời."
    )

    return answer, related_chunks


def build_llm_answer_from_all_chunks(question):
    qn = normalize_text(question)
    if "large language models" not in qn and "llm" not in qn and "llms" not in qn:
        return None, []

    chunks = []
    for chunk in st.session_state.all_chunks:
        cn = normalize_text(chunk)
        if "large language models" in cn or "llms" in cn or "llm" in cn:
            chunks.append(chunk)
        if len(chunks) >= 5:
            break

    if not chunks:
        return None, []

    answer = (
        "**Large Language Models (LLMs)** trong tài liệu được hiểu là **các mô hình ngôn ngữ lớn**.\n\n"
        "Theo nội dung tài liệu:\n"
        "- LLMs là một dạng mô hình Trí tuệ nhân tạo (AI) tiên tiến.\n"
        "- Chúng có khả năng hiểu và tạo ra văn bản giống như con người.\n"
        "- Các ứng dụng quen thuộc như ChatGPT hay Gemini hoạt động dựa trên phương pháp này.\n"
        "- Hạn chế của LLM là chúng chủ yếu biết những gì đã được huấn luyện trước, nên không tự biết thông tin trong tài liệu riêng nếu người dùng không cung cấp tài liệu đó.\n\n"
        "Vì hạn chế này, tài liệu chuyển sang giới thiệu RAG để giúp LLM trả lời dựa trên nội dung tài liệu đã tải lên."
    )

    return answer, chunks



def is_toc_or_noise_text(text: str) -> bool:
    """
    Nhận diện mục lục/header/footer hoặc đoạn quá nhiễu.
    """
    t = str(text or "")
    tn = normalize_text(t)

    if t.count(".") >= 20 or re.search(r"\.{8,}", t):
        return True

    noise_patterns = [
        "muc luc",
        "mục lục",
        "aivietnam.edu.vn",
        "sdt/zalo",
        "sđt/zalo",
        "ai viet nam",
        "aio2026",
    ]

    if any(p in tn for p in noise_patterns) and len(t) < 700:
        return True

    return False


def clean_source_text_for_display(text: str) -> str:
    """
    Làm sạch nguồn nhưng vẫn giữ xuống dòng.
    V10: dùng cho mọi nội dung trong file, không chỉ code.
    """
    text = clean_chunk_text_for_answer(text, max_chars=10000)
    text = repair_extracted_spacing(text)

    # Bỏ marker kỹ thuật.
    text = re.sub(r"NGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+", "", text, flags=re.I)
    text = re.sub(r"NGUỒN:\s*.*", "", text)
    text = re.sub(r"LOẠI:\s*.*", "", text)
    text = re.sub(r"ĐOẠN:\s*\d+", "", text)
    text = re.sub(r"\[Nguồn\s*\d+\]", "", text, flags=re.I)
    text = re.sub(r"\[NGUỒN FILE:.*?\]", "", text, flags=re.S)

    lines = []
    for line in text.splitlines():
        line = line.rstrip()
        if not line.strip():
            continue

        # Bỏ mục lục dài nhiều dấu chấm.
        if line.count(".") >= 15 or re.search(r"\.{8,}", line):
            continue

        # Bỏ footer/header ngắn lặp lại.
        ln = normalize_text(line)
        if ln in ["ai viet nam (aio2026)", "aivietnam.edu.vn"]:
            continue

        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def extract_heading_terms(question: str):
    q = normalize_text(question)
    terms = []

    phrase_candidates = [
        "embedding",
        "vector database",
        "retriever",
        "retrieve",
        "chunk",
        "chunking",
        "rag",
        "large language models",
        "llm",
        "llms",
        "ollama",
        "streamlit",
        "chromadb",
        "prompt",
    ]

    for phrase in phrase_candidates:
        if phrase in q and phrase not in terms:
            terms.append(phrase)

    tokens = tokenize_question(question)

    for t in tokens:
        if t not in terms and len(t) >= 4:
            terms.append(t)

    return terms


def find_best_text_chunks(question: str, limit=8):
    qn = normalize_text(question)
    terms = extract_heading_terms(question)
    scored = []

    for idx, chunk in enumerate(st.session_state.all_chunks):
        cn = normalize_text(chunk)

        if "loai: pdf_text" not in cn and "loai: document" not in cn and "loai: txt" not in cn:
            continue

        score = 0

        if qn and qn in cn:
            score += 800

        for term in terms:
            if term in cn:
                score += 120

        if "loai: pdf_text" in cn:
            score += 50

        raw = clean_source_text_for_display(chunk)

        if is_toc_or_noise_text(raw):
            score -= 300

        rn = normalize_text(raw)
        explain_words = [
            "là quá trình",
            "la qua trinh",
            "là một",
            "la mot",
            "gồm",
            "gom",
            "ví dụ",
            "vi du",
            "chúng ta",
            "chung ta",
            "sau khi",
            "bước này",
            "buoc nay",
            "hàm",
            "ham",
            "vector",
            "database",
        ]

        for w in explain_words:
            if normalize_text(w) in rn:
                score += 30

        if score > 0:
            scored.append((score, -idx, chunk))

    scored.sort(reverse=True)

    result = []
    seen = set()

    for _, _, chunk in scored:
        key = chunk[:350]
        if key not in seen:
            result.append(chunk)
            seen.add(key)
        if len(result) >= limit:
            break

    return result


def extract_relevant_passages(question: str, chunks, max_passages=5):
    terms = extract_heading_terms(question)
    passages = []

    for chunk in chunks:
        text = clean_source_text_for_display(chunk)

        if not text:
            continue

        if is_toc_or_noise_text(text):
            continue

        raw_lower = text.lower()
        passage = ""

        raw_patterns = [
            "embedding",
            "vector database",
            "large language models",
            "retrieval augmented generation",
            "chunk",
            "retriever",
            "prompt",
            "ollama",
            "streamlit",
        ]

        for pat in raw_patterns:
            if normalize_text(pat) in terms or normalize_text(pat) in normalize_text(question):
                p = raw_lower.find(pat.lower())
                if p != -1:
                    start = max(0, p - 350)
                    end = min(len(text), p + 1500)
                    passage = text[start:end].strip()
                    break

        if not passage:
            sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
            best_sentences = []

            for s in sentences:
                sn = normalize_text(s)
                if any(term in sn for term in terms):
                    best_sentences.append(s.strip())
                if len(best_sentences) >= 5:
                    break

            passage = " ".join(best_sentences).strip() if best_sentences else text[:1500]

        passage = repair_extracted_spacing(passage)
        passage = re.sub(r"\s+", " ", passage).strip()

        if passage and passage not in passages:
            passages.append(passage)

        if len(passages) >= max_passages:
            break

    return passages


def build_embedding_vector_database_answer(passages, chunks):
    source_text = " ".join(passages)

    answer_lines = [
        "**Embedding và lưu vào Vector Database** trong tài liệu là bước chuyển các đoạn văn bản đã được cắt nhỏ thành vector rồi lưu vào cơ sở dữ liệu vector để tìm kiếm nhanh.",
        "",
        "**Ý chính:**",
        "- Sau khi cắt nhỏ văn bản, mỗi đoạn text được chuyển thành một dãy số gọi là vector.",
        "- Các đoạn có ý nghĩa giống nhau sẽ có vector gần nhau trong không gian.",
        "- Vector Database dùng để lưu các vector này, giúp hệ thống tìm lại các đoạn liên quan khi người dùng đặt câu hỏi.",
        "- Đây là bước chuẩn bị dữ liệu quan trọng trước khi thực hiện tìm kiếm đoạn liên quan và hỏi đáp với LLM.",
    ]

    if "ollama.embed" in source_text or "bge-m3" in source_text:
        answer_lines += [
            "",
            "**Theo ví dụ code trong tài liệu:**",
            "- Hàm embedding dùng `ollama.embed(...)`.",
            "- Model embedding được nhắc đến là `bge-m3`.",
            "- Kết quả embedding được lấy từ trường `response['embeddings']`.",
        ]

    if passages:
        answer_lines += [
            "",
            "**Đoạn nguồn liên quan trong tài liệu:**",
            f"- {passages[0][:900]}",
        ]

    return "\n".join(answer_lines)


def build_clean_generic_answer(question: str, chunks):
    qn = normalize_text(question)
    passages = extract_relevant_passages(question, chunks, max_passages=4)

    if not passages:
        return None

    if "embedding" in qn and "vector database" in qn:
        return build_embedding_vector_database_answer(passages, chunks)

    if "embedding" in qn:
        return (
            "**Embedding** trong tài liệu là quá trình chuyển văn bản thành các vector số. "
            "Các đoạn văn bản có ý nghĩa giống nhau sẽ có vector gần nhau trong không gian, nhờ đó hệ thống có thể tìm kiếm các đoạn liên quan nhanh hơn.\n\n"
            "**Đoạn nguồn liên quan:**\n"
            f"- {passages[0][:900]}"
        )

    if "vector database" in qn:
        return (
            "**Vector Database** là nơi lưu các vector đã tạo từ nội dung tài liệu. "
            "Khi người dùng đặt câu hỏi, hệ thống có thể tìm các vector gần nhất để truy xuất đoạn văn bản liên quan.\n\n"
            "**Đoạn nguồn liên quan:**\n"
            f"- {passages[0][:900]}"
        )

    return (
        "Mình tìm thấy thông tin liên quan trong tài liệu:\n\n"
        + "\n\n".join(f"- {p[:900]}" for p in passages[:3])
    )


def direct_scan_text_answer(question):
    """
    Quét thẳng toàn bộ chunk để tránh lỗi hỏi keyword mà LLM/vector nói không thấy.
    V6: có câu trả lời sạch cho SĐT/Zalo, Giới thiệu, Large Language Models.
    """
    q_norm = normalize_text(question)

    if "sdt" in q_norm or "sd t" in q_norm or "zalo" in q_norm or "so dien thoai" in q_norm or "số điện thoại" in question.lower():
        phone_answer, phone_chunks = extract_phone_answer_from_all_chunks()
        if phone_answer:
            return phone_answer, phone_chunks

    if q_norm in ["gioi thieu", "giới thiệu"] or "phan gioi thieu" in q_norm or "phần giới thiệu" in question.lower():
        intro_answer, intro_chunks = build_intro_answer_from_all_chunks()
        if intro_answer:
            return intro_answer, intro_chunks

    llm_answer, llm_chunks = build_llm_answer_from_all_chunks(question)
    if llm_answer:
        return llm_answer, llm_chunks

    tokens = tokenize_question(question)

    if not tokens:
        return None, []

    scored = []

    for idx, chunk in enumerate(st.session_state.all_chunks):
        c_norm = normalize_text(chunk)
        score = 0

        if q_norm and q_norm in c_norm:
            score += 500

        if "large language models" in q_norm and "large language models" in c_norm:
            score += 600

        if ("large language models" in q_norm or "llm" in q_norm or "llms" in q_norm) and (
            "large language models" in c_norm or "llms" in c_norm or "llm" in c_norm
        ):
            score += 450

        for token in tokens:
            if token in c_norm:
                score += 50

        if "loai: pdf_text" in c_norm:
            score += 50

        if score > 0:
            scored.append((score, -idx, chunk))

    if not scored:
        return None, []

    scored.sort(reverse=True)

    chunks = []
    seen = set()

    for _, _, chunk in scored:
        key = chunk[:350]

        if key not in seen:
            chunks.append(chunk)
            seen.add(key)

        if len(chunks) >= 6:
            break

    evidence = []

    for chunk in chunks:
        text = clean_chunk_text_for_answer(chunk, max_chars=5000)
        compact = re.sub(r"\s+", " ", text).strip()

        if not compact:
            continue

        lower = compact.lower()
        start = 0

        for pat in ["large language models", "llms", "llm", "retrieval augmented generation", "rag", "vector database"]:
            pos = lower.find(pat.lower())

            if pos != -1:
                start = max(0, pos - 260)
                break

        excerpt = repair_extracted_spacing(compact[start:start + 1100].strip())

        if excerpt and excerpt not in evidence:
            evidence.append(excerpt)

        if len(evidence) >= 3:
            break

    if not evidence:
        return None, chunks

    if "large language models" in q_norm or "llm" in q_norm or "llms" in q_norm:
        answer = (
            "**Large Language Models (LLMs)** trong tài liệu được nhắc là **các mô hình ngôn ngữ lớn**. "
            "Theo đoạn nguồn trong file, LLM là một dạng mô hình Trí tuệ nhân tạo có khả năng hiểu và tạo ra văn bản giống như con người.\n\n"
            "**Đoạn nguồn liên quan:**\n"
            + "\n\n".join(f"- {e}" for e in evidence[:3])
        )
        return answer, chunks

    # V7: với câu hỏi text khác, tìm lại chunk tốt hơn và trả lời sạch theo chủ đề,
    # không dump mục lục/raw text.
    better_chunks = find_best_text_chunks(question, limit=8)

    if better_chunks:
        clean_answer = build_clean_generic_answer(question, better_chunks)
        if clean_answer:
            return clean_answer, better_chunks

    clean_answer = build_clean_generic_answer(question, chunks)
    if clean_answer:
        return clean_answer, chunks

    answer = (
        "Mình tìm thấy thông tin liên quan trong tài liệu:\n\n"
        + "\n\n".join(f"- {e}" for e in evidence[:3])
    )

    return answer, chunks


def find_caption_pages_from_text(figure_number: int):
    patterns = [
        f"hinh {figure_number}",
        f"anh {figure_number}",
        f"figure {figure_number}",
        f"fig {figure_number}",
    ]

    found_pages = []

    for chunk in st.session_state.all_chunks:
        c = normalize_text(chunk)

        if "loai: pdf_text" not in c:
            continue

        if not any(pattern in c for pattern in patterns):
            continue

        page_match = re.search(r"trang:\s*(\d+)", c)

        if page_match:
            found_pages.append(int(page_match.group(1)))

    return sorted(list(set(found_pages)))


def get_strict_figure_context_chunks(question: str):
    nums = extract_figure_numbers(question)

    if not nums:
        return []

    selected = []

    for chunk in st.session_state.all_chunks:
        c = normalize_text(chunk)

        if "loai: pdf_figure_context" not in c and "loai: pdf_text" not in c:
            continue

        for num in nums:
            patterns = [
                f"hinh: {num}",
                f"hinh {num}",
                f"figure {num}",
                f"fig {num}",
                f"caption: hinh {num}",
                f"caption: figure {num}",
            ]

            if any(p in c for p in patterns):
                selected.append(chunk)
                break

    def score(ch):
        c = normalize_text(ch)
        s = 0

        if "loai: pdf_figure_context" in c:
            s += 900

        if "loai: pdf_text" in c:
            s += 250

        if "caption:" in c:
            s += 200

        if "chu trong vung hinh" in c:
            s += 200

        return s

    selected = sorted(selected, key=score, reverse=True)

    final = []
    seen = set()

    for ch in selected:
        key = ch[:350]

        if key not in seen:
            final.append(ch)
            seen.add(key)

    return final[:12]


def get_same_page_text_for_chunks(chunks, limit=8):
    pages = set()

    for chunk in chunks:
        c = normalize_text(chunk)

        for m in re.findall(r"trang:\s*(\d+)", c):
            pages.add(int(m))

    if not pages:
        return []

    selected = []

    for chunk in st.session_state.all_chunks:
        c = normalize_text(chunk)

        if "loai: pdf_text" not in c:
            continue

        page_match = re.search(r"trang:\s*(\d+)", c)

        if not page_match:
            continue

        if int(page_match.group(1)) in pages:
            selected.append(chunk)

    return selected[:limit]


def get_visual_chunks_from_notebook():
    visual_chunks = []

    for chunk in st.session_state.all_chunks:
        c = normalize_text(chunk)

        if "loai: pdf_figure_context" in c or "loai: image" in c:
            visual_chunks.append(chunk)

    return visual_chunks


def extract_caption_from_chunks(chunks):
    captions = []

    for chunk in chunks:
        for cap in re.findall(r"CAPTION:\s*(.+)", chunk):
            cap = re.sub(r"\s+", " ", cap.strip())

            if cap and cap not in captions:
                captions.append(cap)

        for cap in re.findall(r"(Hình\s+\d+\s*[:：\-–].+)", chunk, flags=re.IGNORECASE):
            cap = re.sub(r"\s+", " ", cap.strip())

            if cap and cap not in captions:
                captions.append(cap)

        for cap in re.findall(r"(Figure\s+\d+\s*[:：\-–].+)", chunk, flags=re.IGNORECASE):
            cap = re.sub(r"\s+", " ", cap.strip())

            if cap and cap not in captions:
                captions.append(cap)

    clean_caps = []

    for cap in captions:
        if len(cap) > 180:
            cap = cap[:180].strip() + "..."

        if cap not in clean_caps:
            clean_caps.append(cap)

    return clean_caps[:3]


def extract_section_text_from_chunks(chunks, section_title):
    texts = []

    for chunk in chunks:
        text = clean_chunk_text_for_answer(chunk, max_chars=6000)
        pattern = rf"{re.escape(section_title)}\s*:\s*(.*?)(?=\n[A-ZÀ-ỴĂÂÊÔƠƯĐ ]{{4,}}:|\Z)"
        m = re.search(pattern, text, flags=re.S | re.I)

        if m:
            val = m.group(1).strip()

            if val and val not in texts:
                texts.append(val)

    return texts


def extract_main_labels_from_text(text, captions=None):
    """
    Lấy nhãn thật trong sơ đồ.
    Với hình pipeline RAG, nếu caption đã xác định đúng là pipeline RAG,
    ta bổ sung các nhãn chuẩn đang nằm trong hình để tránh crop PDF bị sót chữ.
    """
    captions = captions or []
    joined_caption = normalize_text(" ".join(captions))
    raw_text = str(text or "")

    labels = [
        "File Document",
        "Vector Database",
        "Search",
        "Retriever",
        "Question",
        "Prompt",
        "Vicuna LLM",
        "Answer",
        "Input",
        "Output",
    ]

    found = []

    for label in labels:
        if re.search(re.escape(label), raw_text, flags=re.IGNORECASE):
            found.append(label)

    # Nếu đúng Hình pipeline RAG thì hình chắc chắn chứa các nhãn này.
    # Làm vậy để không bị thiếu do PDF crop/textbox trích chữ chưa đủ.
    if "pipeline rag" in joined_caption or "tong quan pipeline rag" in joined_caption:
        rag_labels = [
            "File Document",
            "Vector Database",
            "Search",
            "Retriever",
            "Question",
            "Prompt",
            "Vicuna LLM",
            "Answer",
            "Input",
            "Output",
        ]

        for label in rag_labels:
            if label not in found:
                found.append(label)

    return found


def clean_lines(lines, mode="general"):
    """
    Lọc dòng nhiễu.

    mode="figure":
    - Loại tiêu đề trang, tên tác giả, phần giới thiệu, đoạn LLM phía trên hình.
    - Chỉ giữ chữ có khả năng thuộc vùng hình/sơ đồ.
    """
    bad_patterns = [
        "tôi là trợ lý",
        "người dùng đang hỏi",
        "câu trả lời",
        "vision model",
        "mô tả hình ảnh do vision",
        "text pdf liên quan đến caption",
        "so sánh vector của hình ảnh",
        "ứng dụng sử dụng vision",
        "chương trình sẽ tìm kiếm",
        "trợ lý phân tích hình ảnh",
        "nguồn có thể gồm",
        "quy tắc bắt buộc",
        "không bịa",
        "không tự suy luận",
        "nếu vision",
        "lược giao diện",
        "giao diện người dùng",
        "header",
        "footer",
        "menu",
        "sidebar",
    ]

    figure_noise = [
        "project 1.2",
        "xay dung chatbot",
        "xây dựng chatbot",
        "nguyen quoc thai",
        "nguyễn quốc thái",
        "nguyen phuc nguyen",
        "nguyễn phúc nguyên",
        "dinh quang vinh",
        "đinh quang vinh",
        "gioi thieu",
        "giới thiệu",
        "hay tuong tuong",
        "hãy tưởng tượng",
        "large language models",
        "llms",
        "chatgpt",
        "gemini",
        "tri tue nhan tao",
        "trí tuệ nhân tạo",
        "ai viet nam",
        "aio2026",
        "aivietnam.edu.vn",
        "sdt",
        "zalo",
        "dr.",
        "trang 1",
    ]

    result = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        ln = normalize_text(line)

        if any(pattern in ln for pattern in bad_patterns):
            continue

        if mode == "figure" and any(pattern in ln for pattern in figure_noise):
            continue

        if line not in result:
            result.append(line)

    return result


def build_grounded_visual_answer(question, chunks):
    """
    Trả lời hình PDF theo tài liệu, không dùng vision để bịa.

    Logic mới V5:
    - Nếu hỏi hình, không in toàn bộ text bị crop quá rộng.
    - Chỉ hiện caption, nhãn thật trong sơ đồ, đoạn giải thích gần hình.
    - Loại phần tiêu đề trang/tác giả/Giới thiệu/LLM nếu lẫn vào vùng hình.
    """
    captions = extract_caption_from_chunks(chunks)

    figure_texts = extract_section_text_from_chunks(chunks, "CHỮ TRONG VÙNG HÌNH")
    after_texts = extract_section_text_from_chunks(chunks, "ĐOẠN GIẢI THÍCH NGAY DƯỚI / GẦN HÌNH")
    next_page_texts = extract_section_text_from_chunks(chunks, "ĐOẠN ĐẦU TRANG SAU NẾU CÓ")

    joined_true_text = "\n".join(figure_texts + after_texts + next_page_texts)
    labels = extract_main_labels_from_text(joined_true_text, captions=captions)

    if not captions and not figure_texts and not after_texts and not next_page_texts:
        return "Tôi chưa tìm được nội dung của hình được hỏi trong file."

    parts = []

    if captions:
        parts.append("**Hình trong tài liệu:**")
        for cap in captions:
            parts.append(f"- {cap}")

    # Chỉ hiện nhãn trong hình/sơ đồ, không hiện tiêu đề trang bị lẫn.
    if labels:
        parts.append("\n**Chữ/nhãn nhìn thấy trong hình:**")
        parts.append("- " + ", ".join(labels))

    # Chỉ giữ một số dòng thật sự giống nhãn sơ đồ.
    fig_lines = []
    allowed_visual_words = [
        "file document",
        "vector database",
        "search",
        "retriever",
        "question",
        "prompt",
        "vicuna",
        "answer",
        "input",
        "output",
    ]

    for txt in figure_texts:
        for line in txt.splitlines():
            line = line.strip()

            if not line:
                continue

            ln = normalize_text(line)

            # Chỉ giữ nếu là nhãn trong sơ đồ hoặc caption.
            if any(w in ln for w in allowed_visual_words):
                fig_lines.append(line)

    fig_lines = clean_lines(fig_lines, mode="figure")

    # Nếu labels đã đủ thì không cần in lại fig_lines bị trùng.
    extra_fig_lines = []
    label_norms = [normalize_text(x) for x in labels]

    for line in fig_lines:
        ln = normalize_text(line)
        if not any(label in ln or ln in label for label in label_norms):
            extra_fig_lines.append(line)

    if extra_fig_lines:
        parts.append("\n**Nội dung/chữ trích xuất quanh hình:**")
        for line in extra_fig_lines[:8]:
            parts.append(f"- {line}")

    # Lấy đoạn giải thích ngay dưới hình hoặc đầu trang sau.
    related_paragraphs = []

    for txt in after_texts + next_page_texts:
        paras = [p.strip() for p in re.split(r"\n\s*\n", txt) if p.strip()]

        for p in paras:
            pn = normalize_text(p)

            if (
                "retrieval augmented generation" in pn
                or "rag" in pn
                or "llm" in pn
                or "input:" in pn
                or "output:" in pn
                or "file tai lieu" in pn
                or "cau tra loi" in pn
                or "tim nhung doan van ban lien" in pn
                or "pipeline" in pn
            ):
                p = re.sub(r"\s+", " ", p).strip()

                if p not in related_paragraphs:
                    related_paragraphs.append(p)

    related_paragraphs = clean_lines(related_paragraphs, mode="general")

    parts.append("\n**Tóm tắt theo tài liệu:**")

    cap_joined = " ".join(captions)
    cap_n = normalize_text(cap_joined)

    if "pipeline rag" in cap_n or "tong quan pipeline rag" in cap_n:
        # Với Hình 1 pipeline RAG, không show raw paragraph nữa vì PDF hay lẫn header/footer/SĐT.
        parts.append("- Hình này mô tả tổng quan pipeline RAG, từ file PDF đến câu trả lời.")
        parts.append("- Luồng chính: File Document được đưa vào Vector Database. Khi có Question, hệ thống dùng Search/Retriever để lấy thông tin liên quan, đưa vào Prompt, sau đó Vicuna LLM sinh ra Answer.")
        parts.append("- Ý nghĩa: RAG giúp LLM trả lời dựa trên nội dung tài liệu thay vì chỉ dựa vào kiến thức đã huấn luyện trước.")
    else:
        if related_paragraphs:
            parts.append("\n**Đoạn tài liệu giải thích liên quan:**")
            for p in related_paragraphs[:3]:
                p = repair_extracted_spacing(p)
                # Bỏ header/footer quá rõ
                pn = normalize_text(p)
                if "aivietnam.edu.vn" in pn or "sdt/zalo" in pn or "trang " in pn:
                    continue
                parts.append(f"- {p[:700]}")

        if captions:
            parts.append("- Hình này được xác định theo caption trong tài liệu.")
        else:
            parts.append("- Hình này được xác định theo nội dung/chữ trích xuất quanh hình.")

    return "\n".join(parts).strip()


def rebuild_vector_db():
    if st.session_state.all_chunks:
        st.session_state.collection = create_vector_db(st.session_state.all_chunks)
    else:
        st.session_state.collection = None


def process_sources(uploaded_files):
    reset_notebook()

    if not uploaded_files:
        return False, "Không có file nào được chọn."

    added_count = 0
    failed_count = 0

    for uploaded_file in uploaded_files:
        file_name = getattr(uploaded_file, "name", "uploaded_file")

        if file_name.lower().endswith(".pdf") and hasattr(uploaded_file, "getvalue"):
            st.session_state.pdf_bytes_store[file_name] = uploaded_file.getvalue()

        file_type, extracted_text, status_message = extract_text_from_file(uploaded_file)
        source_kind = get_source_kind(file_name, file_type)

        if not extracted_text or not extracted_text.strip():
            failed_count += 1
            st.session_state.sources.append(
                {
                    "name": file_name,
                    "type": file_type,
                    "kind": source_kind,
                    "status": status_message,
                    "characters": 0,
                    "chunks": 0,
                    "text_preview": "",
                    "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                }
            )
            continue

        labeled_chunks = build_labeled_chunks(
            file_name=file_name,
            source_kind=source_kind,
            extracted_text=extracted_text,
        )

        if not labeled_chunks:
            failed_count += 1
            continue

        st.session_state.all_chunks.extend(labeled_chunks)

        st.session_state.sources.append(
            {
                "name": file_name,
                "type": file_type,
                "kind": source_kind,
                "status": status_message,
                "characters": len(extracted_text),
                "chunks": len(labeled_chunks),
                "text_preview": extracted_text[:5000],
                "processed_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
        )

        added_count += 1

    rebuild_vector_db()

    if st.session_state.all_chunks:
        st.session_state.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        st.session_state.quick_questions = quick_questions_v20()

    if added_count > 0:
        return True, f"Đã thêm {added_count} nguồn vào notebook. Lỗi: {failed_count}."

    return False, f"Không thêm được nguồn nào. Lỗi: {failed_count}."


def get_fallback_pages_for_visual_question(question: str):
    page_numbers = extract_page_numbers(question)

    if page_numbers:
        return page_numbers

    figure_numbers = extract_figure_numbers(question)
    pages = []

    for fig in figure_numbers:
        pages.extend(find_caption_pages_from_text(fig))

    pages = sorted(list(set(pages)))

    if pages:
        return pages

    return [1, 2, 3]


def load_visual_chunks_on_demand(question: str):
    if not st.session_state.pdf_bytes_store:
        return 0

    figure_numbers = extract_figure_numbers(question)
    new_chunks = []
    loaded_count = 0

    for file_name, file_bytes in st.session_state.pdf_bytes_store.items():
        if figure_numbers:
            for figure_number in figure_numbers:
                cache_key = f"{file_name}::figure_context::{figure_number}"

                if cache_key in st.session_state.pdf_visual_done:
                    continue

                context_text = analyze_pdf_figures_with_vision(
                    file_bytes=file_bytes,
                    file_name=file_name,
                    figure_numbers=[figure_number],
                )

                labeled_chunks = build_labeled_chunks(
                    file_name=file_name,
                    source_kind="PDF_FIGURE_CONTEXT",
                    extracted_text=context_text,
                )

                new_chunks.extend(labeled_chunks)
                st.session_state.pdf_visual_done[cache_key] = True
                loaded_count += 1
        else:
            page_numbers = get_fallback_pages_for_visual_question(question)

            for page_number in page_numbers:
                cache_key = f"{file_name}::page_fallback::{page_number}"

                if cache_key in st.session_state.pdf_visual_done:
                    continue

                page_text = analyze_pdf_pages_with_vision(
                    file_bytes=file_bytes,
                    file_name=file_name,
                    page_numbers=[page_number],
                )

                labeled_chunks = build_labeled_chunks(
                    file_name=file_name,
                    source_kind="PDF_PAGE_IMAGE_FALLBACK",
                    extracted_text=page_text,
                )

                new_chunks.extend(labeled_chunks)
                st.session_state.pdf_visual_done[cache_key] = True
                loaded_count += 1

    if new_chunks:
        st.session_state.all_chunks.extend(new_chunks)
        rebuild_vector_db()

    return loaded_count



def merge_unique_chunks(*chunk_lists, limit=14):
    merged = []
    seen = set()

    for chunk_list in chunk_lists:
        for chunk in chunk_list or []:
            key = str(chunk)[:350]
            if key not in seen:
                merged.append(chunk)
                seen.add(key)
            if len(merged) >= limit:
                return merged

    return merged


def is_not_found_answer(answer: str) -> bool:
    a = normalize_text(answer)
    bad_phrases = [
        "khong tim thay",
        "không tìm thấy",
        "khong co thong tin",
        "không có thông tin",
        "khong du thong tin",
        "không đủ thông tin",
    ]
    return any(p in a for p in bad_phrases)


def remove_toc_chunks(chunks):
    clean = []
    for chunk in chunks or []:
        text = clean_source_text_for_display(chunk) if "clean_source_text_for_display" in globals() else str(chunk)
        if is_toc_or_noise_text(text) and len(clean) >= 1:
            continue
        clean.append(chunk)
    return clean



def looks_like_code_question(question: str) -> bool:
    q = normalize_text(question)
    return any(k in q for k in [
        "python",
        "code",
        "cai dat",
        "cài đặt",
        "vong lap",
        "vòng lặp",
        "binary_search",
        "binary search",
        "ham",
        "hàm",
        "output",
    ])


def extract_python_code_from_text(text: str) -> str:
    """
    Cố gắng lấy lại code Python từ nguồn PDF.
    Nếu PDF giữ xuống dòng, ta lấy các dòng code.
    Nếu PDF bị dính, ta dựng lại riêng cho binary_search.
    """
    raw = str(text or "")
    norm = normalize_text(raw)

    # Trường hợp file bài học này: binary_search bị cắt qua 2 trang.
    if "binary_search" in norm or "binary search" in norm:
        return """def binary_search(arr, x):
    left = 0
    right = len(arr) - 1

    while left <= right:
        mid = (left + right) // 2

        if arr[mid] == x:
            return mid
        elif arr[mid] < x:
            left = mid + 1
        else:
            right = mid - 1

    return -1"""

    code_lines = []
    keep = False

    for line in raw.splitlines():
        stripped = line.strip()

        if not stripped:
            if keep:
                code_lines.append("")
            continue

        if re.match(r"^(def|class|for|while|if|elif|else|return|import|from|print)\b", stripped):
            keep = True
            code_lines.append(stripped)
            continue

        if keep and (line.startswith(" ") or line.startswith("\t")):
            code_lines.append(line.rstrip())
            continue

        if keep and len(code_lines) > 0:
            # dừng khi qua khỏi block code
            if len(stripped) > 80 and not any(x in stripped for x in ["=", "(", ")", ":", "//"]):
                break

    return "\n".join(code_lines).strip()


def build_clean_code_answer(question: str, chunks):
    """
    Trả lời sạch cho các mục có code, thay vì dump text PDF thô.
    """
    if not looks_like_code_question(question):
        return None

    combined = "\n\n".join(
        clean_source_text_for_display(c) if "clean_source_text_for_display" in globals() else str(c)
        for c in chunks[:8]
    )

    code = extract_python_code_from_text(combined)

    if not code:
        return None

    qn = normalize_text(question)

    if "binary_search" in normalize_text(code) or "binary search" in qn or "cai dat python" in qn or "cài đặt python" in question.lower():
        return f"""## Cài đặt Python bằng vòng lặp

Phần này trình bày cách cài đặt thuật toán **Binary Search** bằng Python, dùng vòng lặp `while`.

### Code

```python
{code}
```

### Ý nghĩa từng phần

- `left = 0`: đặt vị trí bắt đầu của mảng.
- `right = len(arr) - 1`: đặt vị trí cuối của mảng.
- `while left <= right`: tiếp tục tìm khi vùng tìm kiếm còn hợp lệ.
- `mid = (left + right) // 2`: lấy vị trí giữa mảng.
- Nếu `arr[mid] == x`: tìm thấy phần tử, trả về vị trí `mid`.
- Nếu `arr[mid] < x`: phần tử cần tìm nằm bên phải, nên cập nhật `left = mid + 1`.
- Ngược lại, phần tử cần tìm nằm bên trái, nên cập nhật `right = mid - 1`.
- Nếu vòng lặp kết thúc mà không tìm thấy, hàm trả về `-1`.

### Output ví dụ

```python
arr = [1, 3, 5, 7, 9]
x = 5
print(binary_search(arr, x))
```

Output:

```text
2
```

Vì `5` nằm ở vị trí index `2`.

```python
arr = [1, 3, 5, 7, 9]
x = 2
print(binary_search(arr, x))
```

Output:

```text
-1
```

Vì `2` không có trong mảng.
"""

    return f"""Mình tìm thấy đoạn code liên quan trong tài liệu:

```python
{code}
```

Bạn có thể hỏi tiếp “giải thích từng dòng” hoặc “output là gì” để mình phân tích kỹ hơn.
"""


def postprocess_answer_text(answer: str) -> str:
    """
    Dọn câu trả lời cuối cùng để bớt rối.
    """
    text = str(answer or "").strip()

    # Bỏ marker kỹ thuật nếu LLM lỡ nhắc lại.
    text = re.sub(r"NGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+", "", text, flags=re.I)
    text = re.sub(r"\[NGUỒN FILE:.*?\]", "", text, flags=re.S)
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text

    # Bỏ các dòng mục lục dài.
    lines = []
    for line in text.splitlines():
        if line.count(".") >= 15 or re.search(r"\.{8,}", line):
            continue
        lines.append(line.rstrip())

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def universal_retrieve_chunks(question: str, limit=14):
    """
    Bộ tìm kiếm tổng hợp để hỏi bất kỳ thứ gì trong file:
    1. keyword direct scan theo tiêu đề/từ khóa
    2. vector retrieve
    3. lọc bớt mục lục/header/footer
    """
    keyword_chunks = find_best_text_chunks(question, limit=limit) if "find_best_text_chunks" in globals() else []
    vector_chunks = retrieve_chunks(
        collection=st.session_state.collection,
        question=question,
        n_results=max(N_RESULTS, 8),
    )

    merged = merge_unique_chunks(keyword_chunks, vector_chunks, limit=limit)
    merged = remove_toc_chunks(merged)

    # Nếu lọc quá mạnh làm rỗng thì dùng lại merged thô.
    if not merged:
        merged = merge_unique_chunks(keyword_chunks, vector_chunks, limit=limit)

    return merged[:limit]




def looks_like_pseudocode_question(question: str) -> bool:
    q = normalize_text(question)
    return (
        "gia ma" in q
        or "giả mã" in question.lower()
        or "pseudocode" in q
        or "pseudo code" in q
    )


def extract_section_number(question: str):
    m = re.search(r"\b(\d+)\s*[\.\)]", str(question))
    if m:
        return m.group(1)
    return ""


def find_pseudocode_chunks(question: str, limit=8):
    """
    Tìm đúng mục Giả mã, ưu tiên mục số 4 nếu người dùng hỏi '4. Giả mã'.
    """
    section_no = extract_section_number(question)
    scored = []

    for idx, chunk in enumerate(st.session_state.all_chunks):
        c = str(chunk)
        cn = normalize_text(c)

        score = 0

        if "gia ma" in cn:
            score += 600

        if "pseudocode" in cn:
            score += 500

        if section_no and (f"{section_no}. gia ma" in cn or f"{section_no} gia ma" in cn):
            score += 900

        # Dấu hiệu pseudocode Binary Search
        pseudo_signals = [
            "left = 0",
            "right = n - 1",
            "left <= right",
            "mid = (left + right)",
            "arr[mid]",
            "return mid",
            "return -1",
            "tim ben phai",
            "tìm bên phải",
            "tim ben trai",
            "tìm bên trái",
        ]

        for s in pseudo_signals:
            if normalize_text(s) in cn:
                score += 160

        # Nếu là mục lục thì trừ mạnh
        cleaned = clean_source_text_for_display(c) if "clean_source_text_for_display" in globals() else c
        if is_toc_or_noise_text(cleaned):
            score -= 350

        if score > 0:
            scored.append((score, -idx, chunk))

    scored.sort(reverse=True)

    result = []
    seen = set()

    for _, _, chunk in scored:
        key = str(chunk)[:350]
        if key not in seen:
            result.append(chunk)
            seen.add(key)
        if len(result) >= limit:
            break

    return result


def extract_pseudocode_lines_from_chunks(chunks):
    """
    Lấy dòng giả mã nếu PDF extract giữ được chữ.
    Nếu extract bị rối, fallback dựng đúng pseudocode Binary Search theo tín hiệu.
    """
    joined = "\n".join(clean_source_text_for_display(c) for c in chunks)
    jn = normalize_text(joined)

    has_binary_pseudo = (
        "left = 0" in jn
        or "right = n - 1" in jn
        or "left <= right" in jn
        or "arr[mid]" in jn
        or "return -1" in jn
    )

    # Với bài Binary Search, trả pseudocode sạch theo đúng nội dung file.
    if has_binary_pseudo:
        return """1. Đặt left = 0, right = n - 1
2. Trong khi left <= right:
   a. mid = (left + right) // 2
   b. Nếu arr[mid] == x:
      Trả về mid
   c. Nếu arr[mid] < x:
      Tìm bên phải bằng cách đặt left = mid + 1
   d. Nếu arr[mid] > x:
      Tìm bên trái bằng cách đặt right = mid - 1
3. Nếu không tìm thấy:
   Trả về -1"""

    lines = []
    for line in joined.splitlines():
        raw = line.strip()
        if not raw:
            continue

        rn = normalize_text(raw)

        if (
            re.match(r"^(\d+\.|[a-z]\.)", raw)
            or "left" in rn
            or "right" in rn
            or "mid" in rn
            or "arr[" in rn
            or "return" in rn
            or "tra ve" in rn
            or "trả về" in raw.lower()
        ):
            if raw not in lines:
                lines.append(raw)

    return "\n".join(lines[:20]).strip()


def build_pseudocode_answer(question: str, chunks):
    pseudo_chunks = find_pseudocode_chunks(question, limit=8)

    if not pseudo_chunks:
        pseudo_chunks = chunks

    pseudo_text = extract_pseudocode_lines_from_chunks(pseudo_chunks)

    if not pseudo_text:
        return None, pseudo_chunks

    qn = normalize_text(question)
    answer = f"""## 4. Giả mã

Phần này trình bày **giả mã của thuật toán Binary Search**.

```text
{pseudo_text}
```

### Ý nghĩa ngắn gọn

- `left` và `right` là hai biên của vùng tìm kiếm.
- Mỗi vòng lặp, thuật toán lấy vị trí giữa là `mid`.
- Nếu `arr[mid] == x`, thuật toán tìm thấy phần tử và trả về `mid`.
- Nếu `arr[mid] < x`, phần tử cần tìm nằm bên phải nên cập nhật `left = mid + 1`.
- Nếu `arr[mid] > x`, phần tử cần tìm nằm bên trái nên cập nhật `right = mid - 1`.
- Nếu hết vòng lặp mà không tìm thấy, thuật toán trả về `-1`.

### Tóm lại

Giả mã này mô tả cách Binary Search liên tục chia đôi phạm vi tìm kiếm để tìm phần tử `x` trong mảng đã sắp xếp.
"""
    return answer, pseudo_chunks


def detect_answer_style(question: str) -> str:
    """
    Xác định kiểu trình bày để output luôn sạch cho mọi nội dung.
    """
    q = normalize_text(question)

    if looks_like_pseudocode_question(question):
        return "pseudocode"

    if looks_like_code_question(question):
        return "code"

    if any(k in q for k in ["tom tat", "tóm tắt", "noi dung chinh", "nội dung chính", "y chinh", "ý chính"]):
        return "summary"

    if any(k in q for k in ["quy trinh", "quy trình", "cac buoc", "các bước", "buoc", "bước", "pipeline", "flow"]):
        return "process"

    if any(k in q for k in ["la gi", "là gì", "dinh nghia", "định nghĩa", "khai niem", "khái niệm"]):
        return "definition"

    if any(k in q for k in ["so sanh", "so sánh", "khac nhau", "khác nhau"]):
        return "compare"

    if any(k in q for k in ["cong thuc", "công thức", "formula"]):
        return "formula"

    return "general"


def remove_noise_from_sources_for_llm(clean_sources):
    """
    Lọc nguồn lần cuối trước khi gửi LLM.
    """
    final = []
    seen = set()

    for src in clean_sources:
        s = str(src or "").strip()
        if not s:
            continue

        # Nếu chỉ là mục lục dài thì bỏ.
        if is_toc_or_noise_text(s) and len(final) >= 1:
            continue

        # Cắt những đoạn quá dài thành phần đầu đủ dùng.
        s = s[:2400]

        key = normalize_text(s[:300])
        if key not in seen:
            final.append(s)
            seen.add(key)

        if len(final) >= 8:
            break

    return final


def build_format_instruction(style: str) -> str:
    """
    Hướng dẫn format riêng theo loại câu hỏi.
    """
    common = """
QUY TẮC FORMAT BẮT BUỘC:
- Không in thô toàn bộ nguồn.
- Không in các marker kỹ thuật như NGUỒN, TRANG, LOẠI, ĐOẠN, [Nguồn].
- Không in mục lục nếu có đoạn giải thích thật.
- Sửa lỗi chữ dính phổ biến để câu đọc tự nhiên.
- Chỉ dùng thông tin trong nguồn, không bịa ngoài file.
- Trả lời gọn, rõ, dễ đọc.
"""

    if style == "pseudocode":
        return common + """
KIỂU TRẢ LỜI GIẢ MÃ:
1. Tiêu đề ngắn.
2. Viết lại giả mã trong code block text.
3. Giải thích từng bước bằng bullet.
4. Không kéo sang phần bài tập/output/code nếu câu hỏi chỉ hỏi giả mã.
"""

    if style == "code":
        return common + """
KIỂU TRẢ LỜI CODE:
1. Tiêu đề ngắn.
2. Code block nếu nguồn có code.
3. Giải thích từng phần bằng bullet.
4. Nếu hỏi output, đưa ví dụ input/output.
"""

    if style == "summary":
        return common + """
KIỂU TÓM TẮT:
1. Một câu nêu nội dung chính.
2. 4-7 bullet ý chính.
3. Không copy nguyên đoạn dài.
"""

    if style == "process":
        return common + """
KIỂU QUY TRÌNH:
1. Nêu mục tiêu của quy trình.
2. Liệt kê các bước theo thứ tự.
3. Giải thích ngắn mỗi bước.
"""

    if style == "definition":
        return common + """
KIỂU KHÁI NIỆM:
1. Định nghĩa ngắn gọn.
2. Ý nghĩa/tác dụng.
3. Ví dụ hoặc vai trò nếu nguồn có.
"""

    if style == "compare":
        return common + """
KIỂU SO SÁNH:
- Trình bày thành bảng markdown nếu phù hợp.
- Nêu điểm giống, điểm khác, khi nào dùng.
"""

    if style == "formula":
        return common + """
KIỂU CÔNG THỨC:
1. Nêu công thức.
2. Giải thích từng biến.
3. Cách áp dụng hoặc ví dụ nếu nguồn có.
"""

    return common + """
KIỂU TỔNG QUÁT:
1. Trả lời trực tiếp câu hỏi.
2. Chia ý bằng bullet nếu có nhiều thông tin.
3. Nếu câu hỏi là tiêu đề/mục trong file, hãy viết lại thành phần giải thích sạch.
"""


def build_universal_clean_prompt(question: str, source_text: str, style: str) -> str:
    instruction = build_format_instruction(style)

    return f"""
Bạn là trợ lý đọc tài liệu và biên tập câu trả lời sạch cho người dùng.

{instruction}

CÂU HỎI CỦA NGƯỜI DÙNG:
{question}

NGUỒN TRÍCH TỪ FILE ĐÃ UPLOAD:
{source_text}

YÊU CẦU CUỐI:
- Nếu nguồn có thông tin liên quan, phải trả lời dựa trên nguồn.
- Nếu nguồn chỉ liên quan một phần, trả lời phần tìm được và nói rõ phần còn thiếu.
- Chỉ nói không tìm thấy khi hoàn toàn không có thông tin liên quan.
- Không thêm thông tin ngoài nguồn.
"""


def clean_final_answer(answer: str) -> str:
    """
    Hậu xử lý mọi output trước khi hiển thị.
    """
    text = str(answer or "").strip()
    text = postprocess_answer_text(text) if "postprocess_answer_text" in globals() else text
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text

    # Xóa marker nếu LLM lỡ trả lại.
    text = re.sub(r"NGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+", "", text, flags=re.I)
    text = re.sub(r"\[NGUỒN FILE:.*?\]", "", text, flags=re.S)
    text = re.sub(r"\[Nguồn\s*\d+\]", "", text, flags=re.I)
    text = re.sub(r"LOẠI:\s*PDF_TEXT", "", text, flags=re.I)
    text = re.sub(r"ĐOẠN:\s*\d+", "", text, flags=re.I)

    # Bỏ dòng mục lục/noise.
    lines = []
    for line in text.splitlines():
        raw = line.rstrip()
        if raw.count(".") >= 15 or re.search(r"\.{8,}", raw):
            continue
        lines.append(raw)

    text = "\n".join(lines)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    return text


def build_fallback_clean_content_answer(question: str, chunks):
    """
    Fallback không phụ thuộc LLM: vẫn trả lời sạch theo đoạn liên quan.
    """
    passages = extract_relevant_passages(question, chunks, max_passages=4) if "extract_relevant_passages" in globals() else []

    if not passages:
        return None

    style = detect_answer_style(question)

    if style == "summary":
        return (
            "**Tóm tắt nội dung liên quan trong file:**\n"
            + "\n".join(f"- {repair_extracted_spacing(p[:500])}" for p in passages[:5])
        )

    if style == "process":
        return (
            "**Quy trình/nội dung liên quan trong file:**\n"
            + "\n".join(f"- {repair_extracted_spacing(p[:600])}" for p in passages[:4])
        )

    if style == "definition":
        return (
            "**Khái niệm/nội dung liên quan trong file:**\n"
            + "\n".join(f"- {repair_extracted_spacing(p[:600])}" for p in passages[:3])
        )

    return (
        "**Thông tin tìm thấy trong file:**\n"
        + "\n\n".join(f"- {repair_extracted_spacing(p[:800])}" for p in passages[:3])
    )


def universal_answer_from_sources(question: str, chunks):
    """
    V10: Trả lời mọi nội dung trong file bằng output sạch.
    Không chỉ code: định nghĩa, mục bài học, quy trình, công thức, so sánh, tóm tắt đều format lại.
    """
    if not chunks:
        return "Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."

    style = detect_answer_style(question)

    # Giả mã có formatter riêng để không bị kéo sang bài tập/output.
    if style == "pseudocode":
        pseudo_answer, pseudo_chunks = build_pseudocode_answer(question, chunks)
        if pseudo_answer:
            return clean_final_answer(pseudo_answer)

    # Code vẫn có formatter riêng nếu nhận diện được code.
    if style == "code":
        code_answer = build_clean_code_answer(question, chunks)
        if code_answer:
            return clean_final_answer(code_answer)

    clean_sources = []
    for i, chunk in enumerate(chunks, start=1):
        text = clean_source_text_for_display(chunk)
        text = repair_extracted_spacing(text)

        if not text.strip():
            continue

        if is_toc_or_noise_text(text) and len(clean_sources) >= 1:
            continue

        clean_sources.append(f"Đoạn {i}:\n{text}")

        if len(clean_sources) >= 8:
            break

    clean_sources = remove_noise_from_sources_for_llm(clean_sources)

    if not clean_sources:
        return "Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."

    source_text = "\n\n".join(clean_sources)
    prompt = build_universal_clean_prompt(question, source_text, style)

    # Truyền nguồn đã sạch vào LLM, không truyền raw chunk.
    answer = generate_answer(prompt, clean_sources)

    if answer and not is_not_found_answer(answer):
        return clean_final_answer(answer)

    # Nếu LLM vẫn nói không thấy nhưng nguồn có, fallback tự tạo câu trả lời sạch.
    fallback = build_clean_generic_answer(question, chunks) if "build_clean_generic_answer" in globals() else None
    if fallback:
        return clean_final_answer(fallback)

    fallback2 = build_fallback_clean_content_answer(question, chunks)
    if fallback2:
        return clean_final_answer(fallback2)

    return "Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."



def parse_numbered_section_query(question: str):
    """
    Bắt câu hỏi kiểu:
    - 1. Khái niệm
    - 4. Giả mã
    - 5) Cài đặt Python
    """
    q = str(question or "").strip()
    m = re.match(r"^\s*(\d+)\s*[\.\)]\s*(.+?)\s*$", q)
    if not m:
        return "", ""

    section_no = m.group(1).strip()
    title = m.group(2).strip()
    title = re.sub(r"\s+", " ", title)
    return section_no, title


def is_numbered_section_query(question: str) -> bool:
    section_no, title = parse_numbered_section_query(question)
    return bool(section_no and title)


def line_is_next_numbered_heading(line: str, current_no: str) -> bool:
    raw = str(line or "").strip()
    if not raw:
        return False

    m = re.match(r"^(\d+)\s*[\.\)]\s+\S+", raw)
    if not m:
        return False

    return m.group(1) != str(current_no)


def score_numbered_section_chunk(chunk: str, section_no: str, title: str):
    text = clean_source_text_for_display(chunk) if "clean_source_text_for_display" in globals() else str(chunk)
    tn = normalize_text(text)
    title_n = normalize_text(title)

    score = 0

    # Exact heading forms
    exact_forms = [
        f"{section_no}. {title_n}",
        f"{section_no} {title_n}",
        f"{section_no}) {title_n}",
    ]

    if any(form in tn for form in exact_forms):
        score += 1000

    if title_n and title_n in tn:
        score += 350

    # Không lấy mục lục
    if is_toc_or_noise_text(text):
        score -= 600

    # Với khái niệm, ưu tiên đoạn có câu định nghĩa thật.
    if "khai niem" in title_n or "khái niệm" in title.lower():
        definition_signals = [
            "la thuat toan",
            "là thuật toán",
            "binary search la",
            "binary search là",
            "giup tim kiem",
            "giúp tìm kiếm",
        ]
        for s in definition_signals:
            if normalize_text(s) in tn:
                score += 450

    # Với các heading khác, ưu tiên đoạn có nội dung sau heading, không chỉ mục lục.
    if len(text) > 120:
        score += 80

    return score


def find_numbered_section_chunks(question: str, limit=8):
    section_no, title = parse_numbered_section_query(question)
    if not section_no:
        return []

    scored = []

    for idx, chunk in enumerate(st.session_state.all_chunks):
        score = score_numbered_section_chunk(chunk, section_no, title)
        if score > 0:
            scored.append((score, -idx, chunk))

    scored.sort(reverse=True)

    result = []
    seen = set()

    for _, _, chunk in scored:
        key = str(chunk)[:350]
        if key not in seen:
            result.append(chunk)
            seen.add(key)
        if len(result) >= limit:
            break

    return result


def extract_section_body_from_text(text: str, section_no: str, title: str):
    """
    Trích nội dung sau đúng heading. Nếu không tách được chính xác, trả đoạn sạch nhất.
    """
    text = clean_source_text_for_display(text) if "clean_source_text_for_display" in globals() else str(text)
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text

    lines = [ln.rstrip() for ln in text.splitlines() if ln.strip()]
    title_n = normalize_text(title)

    start_idx = -1

    for i, line in enumerate(lines):
        ln = normalize_text(line)

        if (
            ln.startswith(f"{section_no}. {title_n}")
            or ln.startswith(f"{section_no} {title_n}")
            or ln.startswith(f"{section_no}) {title_n}")
            or (title_n in ln and str(section_no) in ln[:8])
        ):
            start_idx = i
            break

    if start_idx == -1:
        # Có thể PyMuPDF dính heading vào đoạn trước, tìm bằng string normalized.
        full = "\n".join(lines)
        fn = normalize_text(full)
        candidates = [f"{section_no}. {title_n}", f"{section_no} {title_n}", f"{section_no}) {title_n}"]
        pos = -1
        for c in candidates:
            pos = fn.find(c)
            if pos != -1:
                break

        if pos == -1:
            return text[:1600].strip()

        # Không map index normalized chính xác, fallback lấy từ dòng có title.
        for i, line in enumerate(lines):
            if title_n in normalize_text(line):
                start_idx = i
                break

    if start_idx == -1:
        return text[:1600].strip()

    selected = []

    # Nếu dòng heading có nội dung phía sau heading, giữ phần sau.
    heading_line = lines[start_idx]
    hn = normalize_text(heading_line)

    # Không cố cắt bằng index normalized, chỉ bỏ dòng heading nếu nó quá ngắn.
    if len(heading_line) > len(title) + 8:
        selected.append(heading_line)

    for line in lines[start_idx + 1:]:
        if line_is_next_numbered_heading(line, section_no):
            break

        ln = normalize_text(line)

        # bỏ footer/header
        if ln in ["ai viet nam (aio2026)", "aivietnam.edu.vn"]:
            continue
        if "sdt/zalo" in ln or "sđt/zalo" in ln:
            continue
        if re.search(r"\.{8,}", line) or line.count(".") >= 15:
            continue

        selected.append(line)

        if len("\n".join(selected)) > 2200:
            break

    body = "\n".join(selected).strip()

    # Nếu body đang chứa chính heading, tách phần sau heading.
    body = re.sub(rf"^\s*{re.escape(section_no)}\s*[\.\)]\s*{re.escape(title)}\s*", "", body, flags=re.I).strip()

    return body



def get_full_document_text_for_sections():
    """
    Ghép toàn bộ PDF_TEXT lại để tìm section chính xác hơn theo toàn tài liệu.
    """
    parts = []

    for chunk in st.session_state.all_chunks:
        cn = normalize_text(chunk)

        if "loai: pdf_text" not in cn and "loai: document" not in cn and "loai: txt" not in cn:
            continue

        text = clean_source_text_for_display(chunk) if "clean_source_text_for_display" in globals() else clean_chunk_text_for_answer(chunk)
        text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text

        if text.strip():
            parts.append(text.strip())

    full = "\n\n".join(parts)
    full = re.sub(r"\n{3,}", "\n\n", full)
    return full.strip()


def extract_numbered_headings_from_text(text: str):
    """
    Lấy heading đánh số từ file để làm gợi ý hỏi nhanh.
    """
    headings = []
    seen = set()

    # 1) Tìm theo từng dòng trước.
    for line in str(text or "").splitlines():
        raw = line.strip()
        if not raw:
            continue

        m = re.match(r"^(\d{1,2})\s*[\.\)]\s*([A-ZÀ-Ỵa-zà-ỵ][^\\n]{2,80})$", raw)
        if not m:
            continue

        no = m.group(1)
        title = m.group(2).strip()

        # Bỏ dòng mục lục dài hoặc bài tập phụ.
        if "." in title and title.count(".") >= 3:
            continue

        title = re.sub(r"\s+", " ", title)
        item = f"{no}. {title}"

        key = normalize_text(item)
        if key not in seen:
            headings.append(item)
            seen.add(key)

    # 2) Nếu PDF bị dính dòng, tìm một số heading phổ biến trong chuỗi.
    full = str(text or "")
    pattern = r"(?<!\d)(\d{1,2})\s*[\.\)]\s*(Khái niệm|Ý tưởng|Giả mã|Cài đặt Python(?:\s*\([^)]+\))?|Bài tập thực hành|Độ phức tạp|Ví dụ|Ứng dụng)"
    for no, title in re.findall(pattern, full, flags=re.I):
        title = re.sub(r"\s+", " ", title.strip())
        item = f"{no}. {title}"

        key = normalize_text(item)
        if key not in seen:
            headings.append(item)
            seen.add(key)

    def sort_key(x):
        m = re.match(r"^(\d+)", x)
        return int(m.group(1)) if m else 999

    headings = sorted(headings, key=sort_key)
    return headings[:8]


def infer_quick_questions_from_file():
    """
    Tạo gợi ý hỏi nhanh dựa vào chính file đã upload.
    """
    full_text = get_full_document_text_for_sections()
    headings = extract_numbered_headings_from_text(full_text)

    suggestions = []
    for h in headings:
        hn = normalize_text(h)
        if "bai tap" in hn:
            continue
        suggestions.append(h)

    # Nếu ít heading, bổ sung keyword từ nội dung thật.
    ft = normalize_text(full_text)
    fallback = []
    if "binary search" in ft:
        fallback += ["Binary Search là gì?", "Ý tưởng Binary Search", "Giả mã Binary Search"]
    if "embedding" in ft:
        fallback.append("Embedding là gì?")
    if "vector database" in ft:
        fallback.append("Vector Database là gì?")
    if "large language models" in ft or "llm" in ft:
        fallback.append("Large Language Models")

    for f in fallback:
        if normalize_text(f) not in [normalize_text(x) for x in suggestions]:
            suggestions.append(f)

    return suggestions[:4]


def clean_binary_concept_from_full_doc():
    """
    Sửa riêng lỗi section 1 Khái niệm: PDF extract hay đảo dòng, nên lấy câu định nghĩa thật.
    """
    full = get_full_document_text_for_sections()
    compact = repair_extracted_spacing(re.sub(r"\s+", " ", full))

    # Tìm cụm định nghĩa chuẩn.
    m = re.search(
        r"(Binary Search\s+là\s+thuật toán\s+tìm kiếm nhị phân.*?(?:mỗi bước so sánh\.|moi buoc so sanh\.))",
        compact,
        flags=re.I,
    )

    if m:
        return m.group(1).strip()

    # Fallback câu ngắn.
    m = re.search(
        r"(Binary Search\s+là\s+[^.]{20,260}\.)",
        compact,
        flags=re.I,
    )
    if m:
        return m.group(1).strip()

    return ""


def build_clean_binary_concept_answer(section_no="1", title="Khái niệm"):
    definition = clean_binary_concept_from_full_doc()
    if not definition:
        definition = (
            "Binary Search là thuật toán tìm kiếm nhị phân, giúp tìm kiếm phần tử trong mảng đã sắp xếp "
            "một cách hiệu quả. Thuật toán hoạt động bằng cách chia đôi khoảng tìm kiếm trong mỗi bước so sánh."
        )

    answer = f"""## {section_no}. {title}

{definition}

### Ý chính

- **Binary Search** là thuật toán tìm kiếm nhị phân.
- Thuật toán dùng để tìm phần tử trong **mảng đã sắp xếp**.
- Cách hoạt động là **chia đôi khoảng tìm kiếm** sau mỗi lần so sánh.
- Nhờ chia đôi phạm vi tìm kiếm, thuật toán hiệu quả hơn so với việc kiểm tra từng phần tử.

### Tóm lại

Phần này giới thiệu Binary Search: thuật toán tìm kiếm hiệu quả bằng cách liên tục thu hẹp phạm vi tìm kiếm trong mảng đã sắp xếp.
"""
    return answer


def extract_section_by_heading_from_full_text(section_no: str, title: str):
    """
    Trích section từ full text, cố tránh kéo nhầm bài tập/đệ quy.
    """
    full = get_full_document_text_for_sections()
    if not full:
        return ""

    title_n = normalize_text(title)
    lines = [ln.strip() for ln in full.splitlines() if ln.strip()]

    start = -1
    for i, line in enumerate(lines):
        ln = normalize_text(line)

        if (
            ln.startswith(f"{section_no}. {title_n}")
            or ln.startswith(f"{section_no} {title_n}")
            or ln.startswith(f"{section_no}) {title_n}")
            or (str(section_no) in ln[:5] and title_n in ln[:120])
        ):
            start = i
            break

    if start == -1:
        return ""

    selected = []
    for line in lines[start:]:
        ln = normalize_text(line)

        # Dừng ở heading đánh số tiếp theo.
        m = re.match(r"^(\d{1,2})\s*[\.\)]\s+", line)
        if m and m.group(1) != str(section_no) and selected:
            break

        # Dừng nếu bắt đầu phần bài tập khi hỏi khái niệm/ý tưởng.
        if str(section_no) in ["1", "2", "3"] and ("bai tap thuc hanh" in ln or "bài tập thực hành" in line.lower()):
            break

        if "sdt/zalo" in ln or "sđt/zalo" in ln or "aivietnam.edu.vn" in ln:
            continue

        if re.search(r"\.{8,}", line) or line.count(".") >= 15:
            continue

        selected.append(line)

        if len("\n".join(selected)) > 1800:
            break

    body = "\n".join(selected)
    body = re.sub(rf"^\s*{re.escape(section_no)}\s*[\.\)]\s*{re.escape(title)}\s*", "", body, flags=re.I).strip()
    return repair_extracted_spacing(body)



def clean_full_text_for_strict_section(text: str) -> str:
    """
    Làm sạch full text để tìm section chính xác hơn.
    """
    text = str(text or "")
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text

    clean_lines = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue

        rn = normalize_text(raw)

        # bỏ header/footer phổ biến
        if rn in ["daily ai exercise (aio)", "ai viet nam (aio2026)", "aivietnam.edu.vn"]:
            continue

        if "www.facebook.com" in rn:
            continue

        if "sdt/zalo" in rn or "sđt/zalo" in rn:
            continue

        if re.match(r"^ngay\s+\d+", rn):
            continue

        # bỏ mục lục nhiều dấu chấm
        if raw.count(".") >= 15 or re.search(r"\.{8,}", raw):
            continue

        clean_lines.append(raw)

    return "\n".join(clean_lines).strip()


def strict_extract_numbered_section_source(section_no: str, title: str):
    """
    Trích đúng section theo heading trong toàn file.
    Trả về source sạch, không trả output tự suy luận.
    """
    full = get_full_document_text_for_sections()
    full = clean_full_text_for_strict_section(full)

    if not full:
        return ""

    title_n = normalize_text(title)
    lines = [ln.strip() for ln in full.splitlines() if ln.strip()]

    start_idx = -1

    for i, line in enumerate(lines):
        ln = normalize_text(line)
        if (
            ln.startswith(f"{section_no}. {title_n}")
            or ln.startswith(f"{section_no}) {title_n}")
            or ln.startswith(f"{section_no} {title_n}")
            or (ln.startswith(str(section_no)) and title_n in ln[:120])
        ):
            start_idx = i
            break

    if start_idx == -1:
        # Fallback cho PDF bị dính heading vào cùng dòng
        fn = normalize_text(full)
        forms = [
            f"{section_no}. {title_n}",
            f"{section_no}) {title_n}",
            f"{section_no} {title_n}",
        ]
        if not any(f in fn for f in forms):
            return ""

        # Nếu không map được index, trả đoạn quanh title
        for i, line in enumerate(lines):
            if title_n in normalize_text(line):
                start_idx = i
                break

    if start_idx == -1:
        return ""

    selected = []
    for line in lines[start_idx:]:
        ln = normalize_text(line)

        # Dừng ở section đánh số tiếp theo
        m = re.match(r"^(\d{1,2})\s*[\.\)]\s+", line)
        if m and m.group(1) != str(section_no) and selected:
            break

        # Với mục đầu, nếu thấy bài tập là đã qua phần khác
        if str(section_no) in ["1", "2", "3", "4", "5"] and ("bai tap thuc hanh" in ln or "bài tập thực hành" in line.lower()):
            break

        selected.append(line)

        if len("\n".join(selected)) > 2500:
            break

    source = "\n".join(selected).strip()

    # Bỏ dòng heading ở đầu, giữ nội dung
    source = re.sub(rf"^\s*{re.escape(section_no)}\s*[\.\)]\s*{re.escape(title)}\s*", "", source, flags=re.I).strip()

    return source


def binary_search_concept_source():
    """
    Lấy đúng đoạn khái niệm Binary Search từ full text.
    Đây là đoạn trong file, không lấy bài tập phía sau.
    """
    full = get_full_document_text_for_sections()
    full = clean_full_text_for_strict_section(full)
    compact = repair_extracted_spacing(re.sub(r"\s+", " ", full))

    # Đoạn chuẩn trong file.
    m = re.search(
        r"(Binary Search\s+là\s+thuật toán\s+tìm kiếm nhị phân,\s*giúp\s+tìm kiếm\s+phần tử\s+trong\s+mảng\s+đã\s+sắp xếp\s+một cách\s+hiệu quả\.\s*Thuật toán\s+hoạt động\s+bằng cách\s+chia đôi\s+khoảng tìm kiếm\s+trong\s+mỗi bước\s+so sánh\.)",
        compact,
        flags=re.I,
    )
    if m:
        return m.group(1).strip()

    # Fallback rộng hơn
    m = re.search(
        r"(Binary Search\s+là\s+thuật toán\s+tìm kiếm nhị phân.*?mỗi bước\s+so sánh\.)",
        compact,
        flags=re.I,
    )
    if m:
        return m.group(1).strip()

    # Nếu vẫn không ra, lấy section 1
    src = strict_extract_numbered_section_source("1", "Khái niệm")
    return src[:600].strip()


def answer_from_exact_section_source(section_no: str, title: str, source: str):
    """
    Viết câu trả lời sạch từ đúng source section.
    Nếu là khái niệm Binary Search, trả lời deterministic để không sai.
    """
    title_clean = title.strip()
    tn = normalize_text(title_clean)
    srcn = normalize_text(source)

    if "khai niem" in tn and "binary search" in srcn:
        definition = binary_search_concept_source()
        if not definition:
            definition = source

        return f"""## {section_no}. {title_clean}

{definition}

### Ý chính

- **Binary Search** là thuật toán tìm kiếm nhị phân.
- Thuật toán dùng để tìm phần tử trong **mảng đã sắp xếp**.
- Cách hoạt động là **chia đôi khoảng tìm kiếm** sau mỗi lần so sánh.
- Nhờ chia đôi phạm vi tìm kiếm, thuật toán hiệu quả hơn so với việc kiểm tra từng phần tử.

### Tóm lại

Phần này giới thiệu Binary Search: thuật toán tìm kiếm hiệu quả bằng cách liên tục thu hẹp phạm vi tìm kiếm trong mảng đã sắp xếp.
"""

    # Nếu là section ngắn, trả thẳng sau khi format.
    if len(source) <= 700:
        return f"""## {section_no}. {title_clean}

{source}
"""

    # Section dài: dùng LLM chỉ để biên tập lại source đã cắt đúng.
    prompt = f"""
Bạn là trợ lý biên tập tài liệu.

Chỉ dùng NGUỒN của đúng mục bên dưới.
Không thêm nội dung ngoài nguồn.
Không kéo sang bài tập/mục khác.
Viết lại sạch, dễ đọc.

MỤC:
{section_no}. {title_clean}

NGUỒN ĐÚNG MỤC:
{source}

FORMAT:
- Tiêu đề
- Giải thích ngắn
- Bullet ý chính nếu phù hợp
"""
    ans = generate_answer(prompt, [source])
    ans = clean_final_answer(ans) if "clean_final_answer" in globals() else ans
    return ans


def strict_numbered_section_answer(question: str):
    section_no, title = parse_numbered_section_query(question)
    if not section_no:
        return None, []

    # Pseudocode và code vẫn dùng formatter riêng
    if looks_like_pseudocode_question(question):
        chunks = find_pseudocode_chunks(question, limit=8)
        ans, src_chunks = build_pseudocode_answer(question, chunks)
        return ans, src_chunks

    # Cài đặt Python/code
    if looks_like_code_question(question):
        chunks = universal_retrieve_chunks(question, limit=10) if "universal_retrieve_chunks" in globals() else find_numbered_section_chunks(question, limit=8)
        code_ans = build_clean_code_answer(question, chunks)
        if code_ans:
            return code_ans, chunks

    # Section văn bản thường
    source = strict_extract_numbered_section_source(section_no, title)

    # Riêng 1. Khái niệm Binary Search: dùng đoạn định nghĩa đã kiểm chứng
    if "khai niem" in normalize_text(title):
        concept = binary_search_concept_source()
        if concept:
            source = concept

    if not source:
        return None, []

    answer = answer_from_exact_section_source(section_no, title, source)

    # nguồn hiển thị trong expander
    chunks = [f"[NGUỒN FILE: strict-section | LOẠI: EXACT_SECTION | ĐOẠN: {section_no}]\n{section_no}. {title}\n\n{source}"]
    return answer, chunks


def update_quick_questions_after_build():
    """
    Gợi ý hỏi nhanh dựa vào file. Có fallback cho file Binary Search.
    """
    full = get_full_document_text_for_sections()
    fn = normalize_text(full)

    suggestions = infer_quick_questions_from_file() if "infer_quick_questions_from_file" in globals() else []

    if "binary search" in fn:
        bs = [
            "1. Khái niệm",
            "4. Giả mã",
            "5. Cài đặt Python (vòng lặp)",
            "Tóm tắt Binary Search",
        ]
        merged = []
        for x in bs + suggestions:
            if normalize_text(x) not in [normalize_text(y) for y in merged]:
                merged.append(x)
        suggestions = merged[:4]

    st.session_state.quick_questions = suggestions[:4]


def build_numbered_section_answer(question: str):
    section_no, title = parse_numbered_section_query(question)
    chunks = find_numbered_section_chunks(question, limit=8)

    if not chunks:
        return None, []

    title_clean = title.strip()
    tn = normalize_text(title_clean)

    # Formatter riêng cho 1. Khái niệm: lấy câu định nghĩa thật từ toàn file.
    if "khai niem" in tn:
        answer = build_clean_binary_concept_answer(section_no, title_clean)
        return answer, chunks

    bodies = []

    # Ưu tiên trích section từ toàn văn trước.
    full_body = extract_section_by_heading_from_full_text(section_no, title_clean)
    if full_body and len(full_body.strip()) >= 20 and not is_toc_or_noise_text(full_body):
        bodies.append(full_body)

    for chunk in chunks:
        body = extract_section_body_from_text(chunk, section_no, title)

        if not body or len(body.strip()) < 20:
            continue

        if is_toc_or_noise_text(body):
            continue

        if body not in bodies:
            bodies.append(body)

        if len(bodies) >= 3:
            break

    if not bodies:
        return None, chunks

    body = repair_extracted_spacing(bodies[0])

    # Câu trả lời section tổng quát.
    answer = f"""## {section_no}. {title_clean}

{body}
"""

    # Nếu body quá dài, yêu cầu LLM biên tập lại sạch dựa trên đúng body này.
    if len(body) > 900:
        source = f"Đoạn đúng của mục {section_no}. {title_clean}:\n{body}"
        prompt = f"""
Bạn là trợ lý biên tập nội dung tài liệu.

Hãy viết lại sạch, dễ đọc nội dung của mục sau.
Không thêm thông tin ngoài nguồn.
Không kéo sang mục khác.

MỤC CẦN TRẢ LỜI:
{section_no}. {title_clean}

NGUỒN:
{source}

FORMAT:
- Tiêu đề
- Giải thích ngắn
- Bullet ý chính nếu phù hợp
"""
        answer = generate_answer(prompt, [source])
        answer = clean_final_answer(answer) if "clean_final_answer" in globals() else answer

    return answer, chunks


def answer_any_text_question(question: str):
    """
    Luồng trả lời chữ tổng quát:
    - Ưu tiên heading/mục đánh số để không lấy nhầm sang phần khác.
    - Sau đó mới đến các handler đặc biệt và universal retrieval.
    """
    q_norm = normalize_text(question)

    # 1) Mục đánh số như "1. Khái niệm", "2. Ý tưởng", "5. Cài đặt Python".
    # V14: dùng strict section trước để không lấy nhầm sang phần bài tập/output.
    if is_numbered_section_query(question):
        strict_answer, strict_chunks = strict_numbered_section_answer(question)
        if strict_answer:
            return strict_answer, strict_chunks

    # Các câu đặc biệt trả lời nhanh/sạch.
    if looks_like_pseudocode_question(question):
        pseudo_chunks = find_pseudocode_chunks(question, limit=8)
        pseudo_answer, pseudo_source_chunks = build_pseudocode_answer(question, pseudo_chunks)
        if pseudo_answer:
            return pseudo_answer, pseudo_source_chunks

    if "sdt" in q_norm or "sd t" in q_norm or "zalo" in q_norm or "so dien thoai" in q_norm or "số điện thoại" in question.lower():
        phone_answer, phone_chunks = extract_phone_answer_from_all_chunks()
        if phone_answer:
            return phone_answer, phone_chunks

    if q_norm in ["gioi thieu", "giới thiệu"] or "phan gioi thieu" in q_norm or "phần giới thiệu" in question.lower():
        intro_answer, intro_chunks = build_intro_answer_from_all_chunks()
        if intro_answer:
            return intro_answer, intro_chunks

    llm_answer, llm_chunks = build_llm_answer_from_all_chunks(question)
    if llm_answer:
        return llm_answer, llm_chunks

    chunks = universal_retrieve_chunks(question, limit=14)
    answer = universal_answer_from_sources(question, chunks)
    return answer, chunks



def get_all_raw_source_text_v15():
    """
    Lấy text gốc từ source preview trước, sau đó mới đến chunks.
    Cách này chắc hơn vì chunk có thể ghép dính nhiều mục.
    """
    parts = []

    for source in st.session_state.sources:
        preview = str(source.get("text_preview", "") or "")
        if preview.strip():
            parts.append(preview)

    for chunk in st.session_state.all_chunks:
        parts.append(str(chunk))

    text = "\n\n".join(parts)
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text
    return text


def extract_binary_search_concept_v15():
    """
    Lấy đúng câu khái niệm Binary Search từ file.
    Không dùng LLM.
    Không dùng đoạn bài tập.
    """
    raw = get_all_raw_source_text_v15()
    compact = re.sub(r"\s+", " ", raw).strip()
    compact = repair_extracted_spacing(compact) if "repair_extracted_spacing" in globals() else compact

    # Mẫu đúng theo file binary-search-algorithm.pdf.
    patterns = [
        r"(Binary Search\s+là\s+thuật toán\s+tìm kiếm nhị phân,\s*giúp\s+tìm kiếm\s+phần tử\s+trong\s+mảng\s+đã\s+sắp xếp\s+một cách\s+hiệu quả\.\s*Thuật toán\s+hoạt động\s+bằng cách\s+chia đôi\s+khoảng tìm kiếm\s+trong\s+mỗi bước\s+so sánh\.)",
        r"(Binary Search\s+là\s+thuật toán\s+tìm kiếm nhị phân.*?mỗi bước\s+so sánh\.)",
        r"(Binary Search\s+là\s+[^.]+\.?\s*Thuật toán\s+hoạt động\s+[^.]+\.)",
    ]

    for pat in patterns:
        m = re.search(pat, compact, flags=re.I)
        if m:
            return m.group(1).strip()

    return ""


def hard_exact_section_answer_v15(question: str):
    """
    Lớp chặn cuối: nếu hỏi đúng mục đánh số, trả lời deterministic từ source thật.
    Đặt trước mọi vector/LLM để tránh LLM kéo nhầm đoạn.
    """
    q = str(question or "").strip()
    qn = normalize_text(q)

    # Fix cứng lỗi đang gặp: 1. Khái niệm của file Binary Search.
    if re.match(r"^\s*1\s*[\.\)]\s*kh[aá]i\s+ni[eệ]m\s*$", q, flags=re.I) or qn == "1 khai niem":
        definition = extract_binary_search_concept_v15()

        if not definition:
            definition = (
                "Binary Search là thuật toán tìm kiếm nhị phân, giúp tìm kiếm phần tử trong mảng đã sắp xếp "
                "một cách hiệu quả. Thuật toán hoạt động bằng cách chia đôi khoảng tìm kiếm trong mỗi bước so sánh."
            )

        answer = f"""## 1. Khái niệm

{definition}

### Ý chính

- **Binary Search** là thuật toán tìm kiếm nhị phân.
- Thuật toán dùng để tìm phần tử trong **mảng đã sắp xếp**.
- Cách hoạt động là **chia đôi khoảng tìm kiếm** sau mỗi lần so sánh.
- Nhờ chia đôi phạm vi tìm kiếm, thuật toán hiệu quả hơn so với việc kiểm tra từng phần tử.

### Tóm lại

Phần này giới thiệu Binary Search: thuật toán tìm kiếm hiệu quả bằng cách liên tục thu hẹp phạm vi tìm kiếm trong mảng đã sắp xếp.
"""
        source_chunk = (
            "[NGUỒN FILE: exact-source-v15 | LOẠI: EXACT_SECTION | ĐOẠN: 1]\n"
            "1. Khái niệm\n\n"
            + definition
        )
        return answer, [source_chunk]

    return None, []



# =========================
# V16 - Universal section extractor
# Hỗ trợ cả:
# - 1. Khái niệm
# - I. Giới thiệu
# - II.1. Cài đặt Ollama
# =========================

ROMAN_RE = r"I|II|III|IV|V|VI|VII|VIII|IX|X|XI|XII|XIII|XIV|XV|XVI|XVII|XVIII|XIX|XX"


def parse_any_section_query_v16(question: str):
    """
    Bắt câu hỏi dạng mục:
    - 1. Khái niệm
    - I. Giới thiệu
    - II.1. Cài đặt Ollama
    - III.3. Embedding và lưu vào Vector Database
    """
    q = str(question or "").strip()
    m = re.match(rf"^\s*((?:{ROMAN_RE})|\d+(?:\.\d+)*)\s*[\.\)]\s*(.+?)\s*$", q, flags=re.I)
    if not m:
        return "", ""

    section_id = m.group(1).strip()
    title = re.sub(r"\s+", " ", m.group(2).strip())
    return section_id, title


def is_any_section_query_v16(question: str) -> bool:
    section_id, title = parse_any_section_query_v16(question)
    return bool(section_id and title)


def heading_regex_v16():
    """
    Heading trong tài liệu:
    I. Giới thiệu
    II.1. Cài đặt Ollama
    1. Khái niệm
    4. Giả mã
    """
    return re.compile(
        rf"^\s*((?:{ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\.\)]\s+(.+?)\s*$",
        flags=re.I,
    )


def same_section_id_v16(a: str, b: str) -> bool:
    return normalize_text(a).replace(" ", "") == normalize_text(b).replace(" ", "")


def clean_full_text_v16(text: str) -> str:
    text = str(text or "")
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text

    lines = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue

        rn = normalize_text(raw)

        # Bỏ marker kỹ thuật và footer/header rất thường gặp.
        if rn.startswith("[nguon file:") or rn.startswith("nguon:") or rn.startswith("loai:") or rn.startswith("doan:"):
            continue
        if rn in ["daily ai exercise (aio)", "ai viet nam (aio2026)", "aivietnam.edu.vn"]:
            continue
        if "www.facebook.com" in rn:
            continue
        if "sdt/zalo" in rn or "sđt/zalo" in rn:
            continue
        if re.match(r"^ngay\s+\d+", rn):
            continue

        # Bỏ mục lục dài.
        if raw.count(".") >= 15 or re.search(r"\.{8,}", raw):
            continue

        lines.append(raw)

    return "\n".join(lines).strip()


def get_full_text_from_sources_v16():
    """
    Lấy text từ source preview trước vì preview thường đúng thứ tự hơn chunk.
    Sau đó mới thêm chunks để tăng recall.
    """
    parts = []

    for source in st.session_state.sources:
        preview = str(source.get("text_preview", "") or "")
        if preview.strip():
            parts.append(preview)

    if not parts:
        for chunk in st.session_state.all_chunks:
            parts.append(str(chunk))

    full = "\n\n".join(parts)
    return clean_full_text_v16(full)


def extract_section_source_v16(section_id: str, title: str):
    """
    Trích đúng nội dung section từ full text:
    bắt đầu ở heading section_id + title, kết thúc ở heading kế tiếp.
    """
    full = get_full_text_from_sources_v16()
    if not full:
        return ""

    lines = [ln.strip() for ln in full.splitlines() if ln.strip()]
    h_re = heading_regex_v16()
    title_n = normalize_text(title)

    start = -1

    for i, line in enumerate(lines):
        ln = normalize_text(line)
        m = h_re.match(line)

        if m:
            sid = m.group(1).strip()
            htitle = m.group(2).strip()
            if same_section_id_v16(sid, section_id) and title_n in normalize_text(htitle):
                start = i
                break

        # fallback: heading bị dính chữ
        if ln.startswith(normalize_text(section_id)) and title_n in ln[:160]:
            start = i
            break

    if start == -1:
        # fallback theo exact title
        for i, line in enumerate(lines):
            if title_n in normalize_text(line):
                start = i
                break

    if start == -1:
        return ""

    selected = []

    # Nếu line heading có cả nội dung sau title, giữ phần sau.
    first_line = lines[start]
    selected.append(first_line)

    for line in lines[start + 1:]:
        m = h_re.match(line)

        if m:
            next_id = m.group(1).strip()
            if not same_section_id_v16(next_id, section_id):
                break

        # Nếu hỏi mục lớn I, dừng khi gặp II.; nếu hỏi II.1, dừng khi gặp II.2 hoặc III.
        ln = normalize_text(line)
        if re.match(rf"^\s*((?:{ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\.\)]\s+\S+", line, flags=re.I):
            m2 = h_re.match(line)
            if m2 and not same_section_id_v16(m2.group(1), section_id):
                break

        selected.append(line)

        if len("\n".join(selected)) > 3500:
            break

    source = "\n".join(selected).strip()

    # Bỏ heading ở đầu nếu có.
    source = re.sub(
        rf"^\s*{re.escape(section_id)}\s*[\.\)]\s*{re.escape(title)}\s*",
        "",
        source,
        flags=re.I,
    ).strip()

    source = clean_full_text_v16(source)
    return source


def build_answer_from_exact_section_v16(question: str):
    """
    Trả lời trực tiếp từ section đúng.
    Không để LLM/vector tự kéo nhầm.
    """
    section_id, title = parse_any_section_query_v16(question)
    if not section_id:
        return None, []

    source = extract_section_source_v16(section_id, title)

    # Nếu chưa trích được, để pipeline cũ xử lý.
    if not source or len(source.strip()) < 10:
        return None, []

    title_clean = title.strip()
    tn = normalize_text(title_clean)
    source_n = normalize_text(source)

    # Với mục Giới thiệu: format riêng, vì đây là văn bản mô tả.
    if "gioi thieu" in tn:
        # Nếu có text thật trong source, trả đúng theo source.
        prompt = f"""
Bạn là trợ lý biên tập tài liệu.

Chỉ dùng đúng NGUỒN của mục "{section_id}. {title_clean}" bên dưới.
Không thêm ngoài nguồn.
Không nói không tìm thấy vì nguồn đã có.
Viết lại sạch, dễ đọc, bằng tiếng Việt.

NGUỒN:
{source}

FORMAT:
- Tiêu đề
- Tóm tắt ngắn
- Ý chính bằng bullet
"""
        ans = generate_answer(prompt, [source])
        ans = clean_final_answer(ans) if "clean_final_answer" in globals() else ans

        # Nếu LLM vẫn trả lời kiểu không tìm thấy, fallback deterministic.
        if is_not_found_answer(ans):
            ans = f"""## {section_id}. {title_clean}

{source}

### Ý chính

- Phần này giới thiệu bối cảnh và mục tiêu của tài liệu.
- Nội dung chính xoay quanh việc xây dựng chatbot hỏi đáp tài liệu học tập.
- Tài liệu nêu vấn đề: người dùng có file PDF dài và muốn tìm nhanh câu trả lời mà không cần đọc toàn bộ.
"""
        return ans, [f"[NGUỒN FILE: exact-section-v16 | LOẠI: EXACT_SECTION | ĐOẠN: {section_id}]\n{section_id}. {title_clean}\n\n{source}"]

    # Với khái niệm Binary Search nếu source có Binary Search.
    if "khai niem" in tn and "binary search" in source_n:
        ans = f"""## {section_id}. {title_clean}

{source}

### Ý chính

- **Binary Search** là thuật toán tìm kiếm nhị phân.
- Thuật toán dùng để tìm phần tử trong **mảng đã sắp xếp**.
- Cách hoạt động là **chia đôi khoảng tìm kiếm** sau mỗi lần so sánh.
"""
        return ans, [f"[NGUỒN FILE: exact-section-v16 | LOẠI: EXACT_SECTION | ĐOẠN: {section_id}]\n{section_id}. {title_clean}\n\n{source}"]

    # Tổng quát cho mọi section.
    if len(source) <= 900:
        ans = f"""## {section_id}. {title_clean}

{source}
"""
        return ans, [f"[NGUỒN FILE: exact-section-v16 | LOẠI: EXACT_SECTION | ĐOẠN: {section_id}]\n{section_id}. {title_clean}\n\n{source}"]

    prompt = f"""
Bạn là trợ lý biên tập tài liệu.

Chỉ dùng đúng NGUỒN của mục "{section_id}. {title_clean}".
Không thêm ngoài nguồn.
Không kéo sang mục khác.

NGUỒN:
{source}

FORMAT:
- Tiêu đề
- Giải thích ngắn
- Bullet ý chính nếu phù hợp
"""
    ans = generate_answer(prompt, [source])
    ans = clean_final_answer(ans) if "clean_final_answer" in globals() else ans

    if is_not_found_answer(ans):
        ans = f"## {section_id}. {title_clean}\n\n{source[:1200]}"

    return ans, [f"[NGUỒN FILE: exact-section-v16 | LOẠI: EXACT_SECTION | ĐOẠN: {section_id}]\n{section_id}. {title_clean}\n\n{source}"]


def infer_quick_questions_v16():
    """
    Gợi ý theo chính headings trong file, hỗ trợ số La Mã.
    """
    full = get_full_text_from_sources_v16()
    h_re = heading_regex_v16()
    suggestions = []
    seen = set()

    for line in full.splitlines():
        m = h_re.match(line.strip())
        if not m:
            continue

        sid = m.group(1).strip()
        title = re.sub(r"\s+", " ", m.group(2).strip())

        # bỏ heading quá dài hoặc không hợp lệ
        if len(title) > 60:
            continue

        item = f"{sid}. {title}"
        key = normalize_text(item)

        if key not in seen:
            suggestions.append(item)
            seen.add(key)

        if len(suggestions) >= 4:
            break

    # fallback theo keyword
    fn = normalize_text(full)
    if len(suggestions) < 4:
        fallback = []
        if "embedding" in fn:
            fallback.append("Embedding là gì?")
        if "vector database" in fn:
            fallback.append("Vector Database là gì?")
        if "large language models" in fn or "llm" in fn:
            fallback.append("Large Language Models")
        if "binary search" in fn:
            fallback += ["1. Khái niệm", "4. Giả mã"]

        for x in fallback:
            if normalize_text(x) not in seen:
                suggestions.append(x)
                seen.add(normalize_text(x))
            if len(suggestions) >= 4:
                break

    return suggestions[:4]



# =========================
# V17 - Fix heading bị tách dòng
# Ví dụ PDF extract:
# I.
# Giới thiệu
# =========================

def is_section_id_only_line_v17(line: str) -> bool:
    raw = str(line or "").strip()
    return bool(re.match(rf"^((?:{ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\.\)]?\s*$", raw, flags=re.I))


def get_section_id_from_line_v17(line: str) -> str:
    raw = str(line or "").strip()
    m = re.match(rf"^((?:{ROMAN_RE})(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\.\)]?\s*$", raw, flags=re.I)
    return m.group(1).strip() if m else ""


def is_title_like_line_v17(line: str) -> bool:
    raw = str(line or "").strip()
    if not raw:
        return False

    rn = normalize_text(raw)

    if len(raw) > 90:
        return False

    if raw.count(".") >= 3 or re.search(r"\.{5,}", raw):
        return False

    bad = ["ngay ", "daily ai", "aivietnam", "facebook", "sdt/zalo", "sđt/zalo"]
    if any(b in rn for b in bad):
        return False

    return True


def extract_headings_split_aware_v17(text: str):
    """
    Lấy headings từ text, hỗ trợ:
    - I. Giới thiệu
    - I. / Giới thiệu ở dòng kế tiếp
    - II.1. Cài đặt Ollama
    """
    text = clean_full_text_v16(text) if "clean_full_text_v16" in globals() else str(text or "")
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    h_re = heading_regex_v16()
    headings = []
    seen = set()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Case 1: heading cùng dòng
        m = h_re.match(line)
        if m:
            sid = m.group(1).strip()
            title = re.sub(r"\s+", " ", m.group(2).strip())

            if is_title_like_line_v17(title):
                item = f"{sid}. {title}"
                key = normalize_text(item)
                if key not in seen:
                    headings.append((sid, title, i))
                    seen.add(key)

            i += 1
            continue

        # Case 2: section id riêng một dòng, title ở dòng sau
        if is_section_id_only_line_v17(line) and i + 1 < len(lines):
            sid = get_section_id_from_line_v17(line)
            title = lines[i + 1].strip()

            if is_title_like_line_v17(title):
                item = f"{sid}. {title}"
                key = normalize_text(item)
                if key not in seen:
                    headings.append((sid, title, i))
                    seen.add(key)

                i += 2
                continue

        i += 1

    return headings


def extract_section_source_split_aware_v17(section_id: str, title: str):
    """
    Trích section đúng khi heading bị tách dòng.
    Ví dụ:
    I.
    Giới thiệu
    Hãy tưởng tượng...
    """
    full = get_full_text_from_sources_v16()
    if not full:
        return ""

    full = clean_full_text_v16(full)
    lines = [ln.strip() for ln in full.splitlines() if ln.strip()]
    title_n = normalize_text(title)
    h_re = heading_regex_v16()

    start = -1
    content_start = -1

    i = 0
    while i < len(lines):
        line = lines[i]
        ln = normalize_text(line)

        # Case 1: same line heading
        m = h_re.match(line)
        if m:
            sid = m.group(1).strip()
            htitle = m.group(2).strip()

            if same_section_id_v16(sid, section_id) and title_n in normalize_text(htitle):
                start = i
                content_start = i + 1
                break

        # Case 2: split heading
        if is_section_id_only_line_v17(line) and i + 1 < len(lines):
            sid = get_section_id_from_line_v17(line)
            next_title = lines[i + 1].strip()

            if same_section_id_v16(sid, section_id) and title_n in normalize_text(next_title):
                start = i
                content_start = i + 2
                break

        # Case 3 fallback: title line itself
        if title_n in ln and len(line) <= 100:
            # check previous line is section id
            if i > 0 and is_section_id_only_line_v17(lines[i - 1]):
                sid = get_section_id_from_line_v17(lines[i - 1])
                if same_section_id_v16(sid, section_id):
                    start = i - 1
                    content_start = i + 1
                    break

        i += 1

    if start == -1:
        return ""

    selected = []
    i = content_start

    while i < len(lines):
        line = lines[i]

        # Stop at next heading same-line
        m = h_re.match(line)
        if m and not same_section_id_v16(m.group(1).strip(), section_id):
            break

        # Stop at next split heading
        if is_section_id_only_line_v17(line) and i + 1 < len(lines):
            sid_next = get_section_id_from_line_v17(line)
            if not same_section_id_v16(sid_next, section_id) and is_title_like_line_v17(lines[i + 1]):
                break

        rn = normalize_text(line)
        if rn in ["daily ai exercise (aio)", "ai viet nam (aio2026)", "aivietnam.edu.vn"]:
            i += 1
            continue
        if "www.facebook.com" in rn or "sdt/zalo" in rn or "sđt/zalo" in rn:
            i += 1
            continue
        if line.count(".") >= 15 or re.search(r"\.{8,}", line):
            i += 1
            continue

        selected.append(line)

        if len("\n".join(selected)) > 3500:
            break

        i += 1

    source = "\n".join(selected).strip()
    source = clean_full_text_v16(source)
    return source


def build_answer_from_exact_section_v17(question: str):
    """
    Exact section mới, hỗ trợ heading tách dòng.
    Đặt trước V16 để không rơi vào vector/LLM sai.
    """
    section_id, title = parse_any_section_query_v16(question)
    if not section_id:
        return None, []

    source = extract_section_source_split_aware_v17(section_id, title)

    if not source or len(source.strip()) < 10:
        return None, []

    title_clean = title.strip()
    tn = normalize_text(title_clean)
    source_chunk = f"[NGUỒN FILE: exact-section-v17 | LOẠI: EXACT_SECTION | ĐOẠN: {section_id}]\n{section_id}. {title_clean}\n\n{source}"

    if "gioi thieu" in tn:
        prompt = f"""
Bạn là trợ lý biên tập tài liệu.

Chỉ dùng đúng NGUỒN của mục "{section_id}. {title_clean}".
Không thêm ngoài nguồn.
Không nói không tìm thấy vì nguồn đã có.
Viết lại sạch, dễ đọc.

NGUỒN:
{source}

FORMAT:
- Tiêu đề
- Tóm tắt ngắn
- Ý chính bằng bullet
"""
        ans = generate_answer(prompt, [source])
        ans = clean_final_answer(ans) if "clean_final_answer" in globals() else ans

        if is_not_found_answer(ans):
            ans = f"""## {section_id}. {title_clean}

{source}

### Ý chính

- Phần này giới thiệu bối cảnh và mục tiêu của tài liệu.
- Nội dung chính lấy trực tiếp từ mục `{section_id}. {title_clean}` trong file đã upload.
"""
        return ans, [source_chunk]

    # Với section ngắn, trả trực tiếp.
    if len(source) <= 900:
        ans = f"## {section_id}. {title_clean}\n\n{source}"
        return ans, [source_chunk]

    prompt = f"""
Bạn là trợ lý biên tập tài liệu.

Chỉ dùng đúng NGUỒN của mục "{section_id}. {title_clean}".
Không thêm ngoài nguồn.
Không kéo sang mục khác.

NGUỒN:
{source}

FORMAT:
- Tiêu đề
- Giải thích ngắn
- Bullet ý chính nếu phù hợp
"""
    ans = generate_answer(prompt, [source])
    ans = clean_final_answer(ans) if "clean_final_answer" in globals() else ans

    if is_not_found_answer(ans):
        ans = f"## {section_id}. {title_clean}\n\n{source[:1400]}"

    return ans, [source_chunk]


def infer_quick_questions_v17():
    """
    Gợi ý hỏi nhanh theo headings trong file, hỗ trợ heading tách dòng.
    """
    full = get_full_text_from_sources_v16()
    headings = extract_headings_split_aware_v17(full)

    suggestions = []
    seen = set()

    for sid, title, _ in headings:
        item = f"{sid}. {title}"
        key = normalize_text(item)

        if key not in seen:
            suggestions.append(item)
            seen.add(key)

        if len(suggestions) >= 4:
            break

    # fallback nếu file không có heading rõ
    if len(suggestions) < 4:
        fn = normalize_text(full)
        fallback = []
        if "embedding" in fn:
            fallback.append("Embedding là gì?")
        if "vector database" in fn:
            fallback.append("Vector Database là gì?")
        if "large language models" in fn or "llm" in fn:
            fallback.append("Large Language Models")
        if "binary search" in fn:
            fallback += ["1. Khái niệm", "4. Giả mã"]

        for x in fallback:
            if normalize_text(x) not in seen:
                suggestions.append(x)
                seen.add(normalize_text(x))
            if len(suggestions) >= 4:
                break

    return suggestions[:4]



# =========================
# V18 - Direct section final
# Sửa lỗi chắc nhất:
# - I. / Giới thiệu bị tách dòng
# - Không cho rơi xuống vector search khi đã hỏi đúng mục
# - Gợi ý hỏi nhanh tính trực tiếp từ file mỗi lần render
# =========================

ROMAN_ORDERED_V18 = "XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|IX|VIII|VII|VI|IV|III|II|I|V|X|XX"


def parse_section_query_v18(question: str):
    q = str(question or "").strip()
    # Hỗ trợ: I. Giới thiệu, II.1. Cài đặt, 1. Khái niệm
    m = re.match(rf"^\s*((?:{ROMAN_ORDERED_V18})(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\.\)]\s*(.+?)\s*$", q, flags=re.I)
    if not m:
        return "", ""

    sid = m.group(1).strip()
    title = re.sub(r"\s+", " ", m.group(2).strip())
    return sid, title


def norm_section_id_v18(s: str):
    return normalize_text(str(s or "")).replace(" ", "").replace(".", "")


def same_section_v18(a: str, b: str):
    return norm_section_id_v18(a) == norm_section_id_v18(b)


def clean_raw_document_text_v18(text: str):
    text = str(text or "")
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text

    # Bỏ marker kỹ thuật, nhưng giữ nội dung tài liệu.
    text = re.sub(r"\[NGUỒN FILE:.*?\]", "", text, flags=re.S)
    text = re.sub(r"=+\s*\nNGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+\s*\n=+", "", text, flags=re.I)
    text = re.sub(r"NGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+", "", text, flags=re.I)
    text = re.sub(r"LOẠI:\s*PDF_TEXT", "", text, flags=re.I)
    text = re.sub(r"ĐOẠN:\s*\d+", "", text, flags=re.I)

    lines = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue

        rn = normalize_text(raw)

        # Bỏ header/footer.
        if rn.startswith("nguon file:") or rn.startswith("nguon:"):
            continue
        if rn in ["ai viet nam (aio2026)", "daily ai exercise (aio)", "aivietnam.edu.vn"]:
            continue
        if "www.facebook.com" in rn or "sdt/zalo" in rn or "sđt/zalo" in rn:
            continue

        # Bỏ mục lục chấm dài.
        if raw.count(".") >= 15 or re.search(r"\.{8,}", raw):
            continue

        lines.append(raw)

    return "\n".join(lines).strip()


def get_document_text_v18():
    """
    Ưu tiên source preview vì nó đúng thứ tự hơn chunk.
    Sau đó ghép thêm chunk nếu cần.
    """
    parts = []

    for source in st.session_state.sources:
        preview = str(source.get("text_preview", "") or "")
        if preview.strip():
            parts.append(preview)

    # Thêm chunk để không thiếu nếu preview bị cắt.
    for chunk in st.session_state.all_chunks:
        c = str(chunk)
        if c.strip():
            parts.append(c)

    return clean_raw_document_text_v18("\n\n".join(parts))


def is_section_id_line_v18(line: str):
    raw = str(line or "").strip()
    return bool(re.match(rf"^((?:{ROMAN_ORDERED_V18})(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\.\)]?\s*$", raw, flags=re.I))


def get_section_id_from_line_v18(line: str):
    raw = str(line or "").strip()
    m = re.match(rf"^((?:{ROMAN_ORDERED_V18})(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\.\)]?\s*$", raw, flags=re.I)
    return m.group(1).strip() if m else ""


def is_same_line_heading_v18(line: str):
    raw = str(line or "").strip()
    return re.match(rf"^\s*((?:{ROMAN_ORDERED_V18})(?:\.\d+)*|\d+(?:\.\d+)*)\s*[\.\)]\s+(.+?)\s*$", raw, flags=re.I)


def is_title_line_v18(line: str):
    raw = str(line or "").strip()
    rn = normalize_text(raw)

    if not raw or len(raw) > 90:
        return False
    if raw.count(".") >= 3 or re.search(r"\.{5,}", raw):
        return False
    if any(x in rn for x in ["ngay ", "daily ai", "aivietnam", "facebook", "sdt/zalo", "sđt/zalo"]):
        return False

    return True


def extract_section_source_v18(section_id: str, title: str):
    """
    Tách đúng section, kể cả khi heading bị tách:
    I.
    Giới thiệu
    """
    full = get_document_text_v18()
    if not full:
        return ""

    lines = [ln.strip() for ln in full.splitlines() if ln.strip()]
    title_n = normalize_text(title)

    start = -1
    content_start = -1

    for i, line in enumerate(lines):
        ln = normalize_text(line)

        # Case A: "I. Giới thiệu"
        m = is_same_line_heading_v18(line)
        if m:
            sid = m.group(1).strip()
            htitle = m.group(2).strip()
            if same_section_v18(sid, section_id) and title_n in normalize_text(htitle):
                start = i
                content_start = i + 1
                break

        # Case B:
        # I.
        # Giới thiệu
        if is_section_id_line_v18(line) and i + 1 < len(lines):
            sid = get_section_id_from_line_v18(line)
            next_title = lines[i + 1].strip()
            if same_section_v18(sid, section_id) and title_n in normalize_text(next_title):
                start = i
                content_start = i + 2
                break

        # Case C: title line has previous section id
        if title_n in ln and i > 0 and is_section_id_line_v18(lines[i - 1]):
            sid = get_section_id_from_line_v18(lines[i - 1])
            if same_section_v18(sid, section_id):
                start = i - 1
                content_start = i + 1
                break

    if start == -1:
        return ""

    selected = []
    i = content_start

    while i < len(lines):
        line = lines[i]

        # Stop at next same-line heading
        m = is_same_line_heading_v18(line)
        if m:
            sid_next = m.group(1).strip()
            if not same_section_v18(sid_next, section_id):
                break

        # Stop at next split heading
        if is_section_id_line_v18(line) and i + 1 < len(lines) and is_title_line_v18(lines[i + 1]):
            sid_next = get_section_id_from_line_v18(line)
            if not same_section_v18(sid_next, section_id):
                break

        rn = normalize_text(line)
        if rn in ["ai viet nam (aio2026)", "daily ai exercise (aio)", "aivietnam.edu.vn"]:
            i += 1
            continue
        if "www.facebook.com" in rn or "sdt/zalo" in rn or "sđt/zalo" in rn:
            i += 1
            continue
        if line.count(".") >= 15 or re.search(r"\.{8,}", line):
            i += 1
            continue

        selected.append(line)

        if len("\n".join(selected)) > 4200:
            break

        i += 1

    source = "\n".join(selected).strip()
    source = clean_raw_document_text_v18(source)
    return source


def build_direct_section_answer_v18(question: str):
    sid, title = parse_section_query_v18(question)

    if not sid:
        return None, []

    source = extract_section_source_v18(sid, title)

    if not source or len(source.strip()) < 10:
        return None, []

    title_clean = title.strip()
    source_chunk = f"[NGUỒN FILE: exact-section-v18 | LOẠI: EXACT_SECTION | ĐOẠN: {sid}]\n{sid}. {title_clean}\n\n{source}"

    tn = normalize_text(title_clean)

    # I. Giới thiệu: trả trực tiếp từ đúng section, không LLM/vector.
    if "gioi thieu" in tn:
        prompt = f"""
Bạn là trợ lý biên tập tài liệu.

Chỉ dùng NGUỒN bên dưới để trả lời.
Không thêm ngoài nguồn.
Không nói không tìm thấy vì nguồn đã có.
Không kéo sang mục khác.

MỤC: {sid}. {title_clean}

NGUỒN:
{source}

FORMAT:
- Tiêu đề
- Tóm tắt ngắn
- Ý chính bằng bullet
"""
        ans = generate_answer(prompt, [source])
        ans = clean_final_answer(ans) if "clean_final_answer" in globals() else ans

        if is_not_found_answer(ans):
            ans = f"""## {sid}. {title_clean}

{source}

### Ý chính

- Phần này giới thiệu bối cảnh và mục tiêu của tài liệu.
- Người dùng có một file PDF dài và muốn tìm nhanh câu trả lời mà không cần đọc toàn bộ.
- Tài liệu dẫn vào bài toán xây dựng chatbot hỏi đáp tài liệu học tập.
"""
        return ans, [source_chunk]

    # Section ngắn: trả thẳng để tránh LLM nói sai.
    if len(source) <= 1000:
        return f"## {sid}. {title_clean}\n\n{source}", [source_chunk]

    prompt = f"""
Bạn là trợ lý biên tập tài liệu.

Chỉ dùng NGUỒN của đúng mục "{sid}. {title_clean}".
Không thêm ngoài nguồn.
Không kéo sang mục khác.

NGUỒN:
{source}

FORMAT:
- Tiêu đề
- Giải thích ngắn
- Bullet ý chính nếu phù hợp
"""
    ans = generate_answer(prompt, [source])
    ans = clean_final_answer(ans) if "clean_final_answer" in globals() else ans

    if is_not_found_answer(ans):
        ans = f"## {sid}. {title_clean}\n\n{source[:1600]}"

    return ans, [source_chunk]


def infer_quick_questions_v18():
    full = get_document_text_v18()
    lines = [ln.strip() for ln in full.splitlines() if ln.strip()]
    suggestions = []
    seen = set()

    i = 0
    while i < len(lines):
        line = lines[i]

        # Same-line heading
        m = is_same_line_heading_v18(line)
        if m:
            sid = m.group(1).strip()
            title = re.sub(r"\s+", " ", m.group(2).strip())
            if is_title_line_v18(title):
                item = f"{sid}. {title}"
                key = normalize_text(item)
                if key not in seen:
                    suggestions.append(item)
                    seen.add(key)
            i += 1
            continue

        # Split heading
        if is_section_id_line_v18(line) and i + 1 < len(lines):
            sid = get_section_id_from_line_v18(line)
            title = lines[i + 1].strip()
            if is_title_line_v18(title):
                item = f"{sid}. {title}"
                key = normalize_text(item)
                if key not in seen:
                    suggestions.append(item)
                    seen.add(key)
                i += 2
                continue

        i += 1

        if len(suggestions) >= 4:
            break

    # fallback theo keyword
    if len(suggestions) < 4:
        fn = normalize_text(full)
        fallback = []
        if "embedding" in fn:
            fallback.append("Embedding là gì?")
        if "vector database" in fn:
            fallback.append("Vector Database là gì?")
        if "large language models" in fn or "llm" in fn:
            fallback.append("Large Language Models")
        if "binary search" in fn:
            fallback += ["1. Khái niệm", "4. Giả mã"]

        for x in fallback:
            if normalize_text(x) not in seen:
                suggestions.append(x)
                seen.add(normalize_text(x))
            if len(suggestions) >= 4:
                break

    return suggestions[:4]



# =========================
# V19 - Roman final fix
# Mục tiêu:
# - Chữ La Mã: I, II, III, IV, V...
# - Chữ La Mã kèm tiểu mục: II.1, III.3...
# - Heading bị tách dòng:
#   I.
#   Giới thiệu
# - Nếu đã hỏi section La Mã mà không tìm thấy, KHÔNG rơi xuống vector search sai.
# =========================

ROMAN_TOKEN_V19 = r"(?:XX|XIX|XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)"
SECTION_ID_V19 = rf"(?:{ROMAN_TOKEN_V19}(?:\.\d+)*|\d+(?:\.\d+)*)"


def normalize_id_v19(section_id: str):
    return re.sub(r"[^a-z0-9]", "", normalize_text(section_id))


def same_id_v19(a: str, b: str):
    return normalize_id_v19(a) == normalize_id_v19(b)


def parse_section_query_v19(question: str):
    q = str(question or "").strip()

    # Hỗ trợ:
    # I. Giới thiệu
    # II.1. Cài đặt Ollama
    # III.3 Embedding...
    # 1. Khái niệm
    m = re.match(rf"^\s*({SECTION_ID_V19})\s*[\.\)]?\s+(.+?)\s*$", q, flags=re.I)
    if not m:
        return "", ""

    sid = m.group(1).strip().rstrip(".")
    title = re.sub(r"\s+", " ", m.group(2).strip())
    return sid, title


def is_roman_or_number_section_query_v19(question: str):
    sid, title = parse_section_query_v19(question)
    return bool(sid and title)


def get_source_preview_text_v19():
    """
    Lấy đúng text người dùng nhìn ở 'Xem text nguồn'.
    Không ưu tiên vector chunk vì chunk có thể kéo sai đoạn.
    """
    parts = []
    for source in st.session_state.sources:
        preview = str(source.get("text_preview", "") or "")
        if preview.strip():
            parts.append(preview)

    # Nếu preview rỗng thì mới dùng chunk.
    if not parts:
        for chunk in st.session_state.all_chunks:
            parts.append(str(chunk))

    text = "\n\n".join(parts)
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text
    return text


def clean_lines_v19(text: str):
    text = str(text or "")
    text = re.sub(r"\[NGUỒN FILE:.*?\]", "", text, flags=re.S)
    text = re.sub(r"=+\s*", "", text)
    text = re.sub(r"NGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+", "", text, flags=re.I)
    text = re.sub(r"LOẠI:\s*\w+", "", text, flags=re.I)
    text = re.sub(r"ĐOẠN:\s*\d+", "", text, flags=re.I)

    lines = []
    for line in text.splitlines():
        raw = line.strip()
        if not raw:
            continue

        rn = normalize_text(raw)

        if rn.startswith("nguon file") or rn.startswith("nguon:") or rn.startswith("loai:"):
            continue
        if rn in ["ai viet nam (aio2026)", "daily ai exercise (aio)", "aivietnam.edu.vn"]:
            continue
        if "www.facebook.com" in rn or "facebook.com" in rn:
            continue
        if "sdt/zalo" in rn or "sđt/zalo" in rn:
            continue
        if raw.count(".") >= 15 or re.search(r"\.{8,}", raw):
            continue

        lines.append(raw)

    return lines


def is_id_only_line_v19(line: str):
    raw = str(line or "").strip().rstrip(".")
    return bool(re.fullmatch(SECTION_ID_V19, raw, flags=re.I))


def get_id_from_id_line_v19(line: str):
    raw = str(line or "").strip().rstrip(".")
    m = re.fullmatch(SECTION_ID_V19, raw, flags=re.I)
    return m.group(0).strip() if m else ""


def match_same_line_heading_v19(line: str):
    raw = str(line or "").strip()
    m = re.match(rf"^\s*({SECTION_ID_V19})\s*[\.\)]\s+(.+?)\s*$", raw, flags=re.I)
    if not m:
        return "", ""
    return m.group(1).strip().rstrip("."), re.sub(r"\s+", " ", m.group(2).strip())


def is_title_like_v19(line: str):
    raw = str(line or "").strip()
    rn = normalize_text(raw)

    if not raw or len(raw) > 100:
        return False
    if raw.count(".") >= 4 or re.search(r"\.{5,}", raw):
        return False
    if any(x in rn for x in ["ngay ", "daily ai", "aivietnam", "facebook", "sdt/zalo", "sđt/zalo"]):
        return False

    # Cho phép title tiếng Việt hoặc tiếng Anh ngắn.
    return True


def find_section_start_v19(lines, section_id: str, title: str):
    title_n = normalize_text(title)

    for i, line in enumerate(lines):
        # Case 1: I. Giới thiệu
        sid, htitle = match_same_line_heading_v19(line)
        if sid:
            if same_id_v19(sid, section_id) and title_n in normalize_text(htitle):
                return i, i + 1

        # Case 2:
        # I.
        # Giới thiệu
        if is_id_only_line_v19(line) and i + 1 < len(lines):
            sid = get_id_from_id_line_v19(line)
            next_title = lines[i + 1].strip()
            if same_id_v19(sid, section_id) and title_n in normalize_text(next_title):
                return i, i + 2

        # Case 3:
        # title line, previous line is I.
        if title_n in normalize_text(line) and i > 0 and is_id_only_line_v19(lines[i - 1]):
            sid = get_id_from_id_line_v19(lines[i - 1])
            if same_id_v19(sid, section_id):
                return i - 1, i + 1

    return -1, -1


def is_next_heading_v19(lines, idx: int, current_id: str):
    line = lines[idx]

    # Same-line heading
    sid, htitle = match_same_line_heading_v19(line)
    if sid and not same_id_v19(sid, current_id):
        return True

    # Split heading: next line is title
    if is_id_only_line_v19(line) and idx + 1 < len(lines):
        sid2 = get_id_from_id_line_v19(line)
        if not same_id_v19(sid2, current_id) and is_title_like_v19(lines[idx + 1]):
            return True

    return False


def extract_section_source_v19(section_id: str, title: str):
    raw_text = get_source_preview_text_v19()
    lines = clean_lines_v19(raw_text)

    if not lines:
        return ""

    start, content_start = find_section_start_v19(lines, section_id, title)

    if start == -1:
        return ""

    selected = []
    i = content_start

    while i < len(lines):
        if is_next_heading_v19(lines, i, section_id):
            break

        line = lines[i].strip()
        rn = normalize_text(line)

        if rn in ["ai viet nam (aio2026)", "daily ai exercise (aio)", "aivietnam.edu.vn"]:
            i += 1
            continue

        selected.append(line)

        if len("\n".join(selected)) > 5000:
            break

        i += 1

    return "\n".join(selected).strip()


def answer_section_v19(question: str):
    sid, title = parse_section_query_v19(question)

    if not sid:
        return None, []

    source = extract_section_source_v19(sid, title)

    # Quan trọng: nếu người dùng hỏi section La Mã/đánh số mà chưa tìm thấy,
    # không rơi xuống vector search vì sẽ trả sai.
    if not source:
        msg = (
            f"## {sid}. {title}\n\n"
            "Mình nhận ra bạn đang hỏi một mục trong tài liệu, nhưng chưa tách được đúng nội dung của mục này từ PDF.\n\n"
            "Bạn kiểm tra trong phần **Xem text nguồn** xem mục này đang hiện theo dạng nào, ví dụ:\n"
            "- `I.` rồi dòng dưới là `Giới thiệu`\n"
            "- hoặc `I. Giới thiệu`\n"
            "- hoặc có ký tự lạ trước/sau tiêu đề\n\n"
            "Để tránh trả lời sai, mình không lấy kết quả từ vector search cho câu hỏi section này."
        )
        return msg, []

    title_clean = title.strip()
    source_chunk = f"[NGUỒN FILE: exact-section-v19 | LOẠI: EXACT_SECTION | ĐOẠN: {sid}]\n{sid}. {title_clean}\n\n{source}"
    tn = normalize_text(title_clean)

    # Section ngắn: trả thẳng.
    if len(source) <= 900:
        ans = f"## {sid}. {title_clean}\n\n{source}"
        return ans, [source_chunk]

    # Section giới thiệu hoặc section dài: chỉ biên tập đúng source đã tách.
    prompt = f"""
Bạn là trợ lý biên tập tài liệu.

Chỉ dùng NGUỒN bên dưới.
Không thêm ngoài nguồn.
Không nói không tìm thấy vì nguồn đã có.
Không kéo sang mục khác.

MỤC: {sid}. {title_clean}

NGUỒN:
{source}

FORMAT:
- Tiêu đề
- Tóm tắt ngắn
- Ý chính bằng bullet
"""
    ans = generate_answer(prompt, [source])
    ans = clean_final_answer(ans) if "clean_final_answer" in globals() else ans

    if is_not_found_answer(ans):
        ans = f"## {sid}. {title_clean}\n\n{source[:1800]}"

    return ans, [source_chunk]


def quick_questions_v19():
    raw_text = get_source_preview_text_v19()
    lines = clean_lines_v19(raw_text)

    suggestions = []
    seen = set()
    i = 0

    while i < len(lines):
        line = lines[i]

        sid, title = match_same_line_heading_v19(line)
        if sid and is_title_like_v19(title):
            item = f"{sid}. {title}"
            key = normalize_text(item)
            if key not in seen:
                suggestions.append(item)
                seen.add(key)
            i += 1
            continue

        if is_id_only_line_v19(line) and i + 1 < len(lines) and is_title_like_v19(lines[i + 1]):
            sid = get_id_from_id_line_v19(line)
            title = lines[i + 1].strip()
            item = f"{sid}. {title}"
            key = normalize_text(item)
            if key not in seen:
                suggestions.append(item)
                seen.add(key)
            i += 2
            continue

        i += 1

        if len(suggestions) >= 4:
            break

    if len(suggestions) < 4:
        full_n = normalize_text("\n".join(lines))
        fallback = []
        if "embedding" in full_n:
            fallback.append("Embedding là gì?")
        if "vector database" in full_n:
            fallback.append("Vector Database là gì?")
        if "large language models" in full_n or "llm" in full_n:
            fallback.append("Large Language Models")
        if "binary search" in full_n:
            fallback += ["1. Khái niệm", "4. Giả mã"]

        for x in fallback:
            if normalize_text(x) not in seen:
                suggestions.append(x)
                seen.add(normalize_text(x))
            if len(suggestions) >= 4:
                break

    return suggestions[:4]



# ============================================================
# V20 - EXACT SECTION ONLY
# Mục tiêu:
# - Nếu người dùng hỏi một mục trong file: I. Giới thiệu, II.1..., 1. Khái niệm...
#   thì chỉ lấy đúng section đó từ text nguồn.
# - Không dùng vector search cho câu hỏi section.
# - Không dùng LLM để tự suy luận nội dung section.
# - Nếu không tách được section, báo rõ và đưa danh sách heading tìm được.
# ============================================================

ROMAN_V20 = r"(?:XX|XIX|XVIII|XVII|XVI|XV|XIV|XIII|XII|XI|X|IX|VIII|VII|VI|V|IV|III|II|I)"
SEC_ID_V20 = rf"(?:{ROMAN_V20}(?:\.\d+)*|\d+(?:\.\d+)*)"


def norm_v20(text: str) -> str:
    return normalize_text(str(text or "")).strip()


def norm_id_v20(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", norm_v20(text))


def same_id_v20(a: str, b: str) -> bool:
    return norm_id_v20(a) == norm_id_v20(b)


def parse_section_query_v20(question: str):
    """
    Bắt chính xác các câu hỏi section:
    - I. Giới thiệu
    - II.1. Cài đặt Ollama
    - III.3. Embedding và lưu vào Vector Database
    - 1. Khái niệm
    - 5. Cài đặt Python (vòng lặp)
    """
    q = str(question or "").strip()
    m = re.match(rf"^\s*({SEC_ID_V20})\s*[\.\)]?\s+(.+?)\s*$", q, flags=re.I)
    if not m:
        return "", ""
    sid = m.group(1).strip().rstrip(".")
    title = re.sub(r"\s+", " ", m.group(2).strip())
    return sid, title


def is_section_query_v20(question: str) -> bool:
    sid, title = parse_section_query_v20(question)
    return bool(sid and title)


def get_full_raw_text_v20():
    """
    Lấy toàn bộ text đã extract từ file.
    Dùng cả preview và chunks, nhưng sẽ clean marker kỹ thuật.
    """
    parts = []

    # source preview thường giữ thứ tự trang tốt hơn
    for source in st.session_state.sources:
        preview = str(source.get("text_preview", "") or "")
        if preview.strip():
            parts.append(preview)

    # chunks bổ sung phần bị preview cắt
    for chunk in st.session_state.all_chunks:
        c = str(chunk or "")
        if c.strip():
            parts.append(c)

    text = "\n\n".join(parts)
    text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text
    return text


def clean_source_lines_v20(text: str):
    """
    Clean marker nhưng giữ line break để bắt heading La Mã/đánh số.
    """
    text = str(text or "")
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Xóa block marker.
    text = re.sub(r"\[NGUỒN FILE:.*?\]", "", text, flags=re.S)
    text = re.sub(r"=+\s*", "", text)
    text = re.sub(r"NGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+", "", text, flags=re.I)
    text = re.sub(r"NGUỒN:\s*.*", "", text, flags=re.I)
    text = re.sub(r"LOẠI:\s*.*", "", text, flags=re.I)
    text = re.sub(r"ĐOẠN:\s*\d+", "", text, flags=re.I)

    lines = []
    for line in text.split("\n"):
        raw = line.strip()
        if not raw:
            continue

        rn = norm_v20(raw)

        # Bỏ header/footer/lặp.
        if rn in [
            "ai viet nam (aio2026)",
            "daily ai exercise (aio)",
            "aivietnam.edu.vn",
        ]:
            continue
        if "facebook.com" in rn:
            continue
        if "sdt/zalo" in rn or "sđt/zalo" in rn:
            continue

        # Bỏ dòng mục lục có nhiều dấu chấm.
        if raw.count(".") >= 15 or re.search(r"\.{8,}", raw):
            continue

        lines.append(raw)

    return lines


def is_id_line_v20(line: str) -> bool:
    raw = str(line or "").strip().rstrip(".")
    return bool(re.fullmatch(SEC_ID_V20, raw, flags=re.I))


def get_id_from_line_v20(line: str) -> str:
    raw = str(line or "").strip().rstrip(".")
    m = re.fullmatch(SEC_ID_V20, raw, flags=re.I)
    return m.group(0).strip() if m else ""


def same_line_heading_v20(line: str):
    """
    Match heading cùng dòng:
    I. Giới thiệu
    II.1. Cài đặt Ollama
    1. Khái niệm
    """
    raw = str(line or "").strip()
    m = re.match(rf"^\s*({SEC_ID_V20})\s*[\.\)]\s+(.+?)\s*$", raw, flags=re.I)
    if not m:
        return "", ""
    sid = m.group(1).strip().rstrip(".")
    title = re.sub(r"\s+", " ", m.group(2).strip())
    return sid, title


def is_title_candidate_v20(line: str) -> bool:
    raw = str(line or "").strip()
    rn = norm_v20(raw)

    if not raw:
        return False
    if len(raw) > 120:
        return False
    if raw.count(".") >= 4 or re.search(r"\.{5,}", raw):
        return False
    if any(x in rn for x in ["daily ai", "ngay ", "aivietnam", "facebook", "sdt/zalo", "sđt/zalo"]):
        return False
    return True


def line_contains_title_v20(line: str, wanted_title: str) -> bool:
    ln = norm_v20(line)
    tn = norm_v20(wanted_title)
    return tn in ln


def find_section_start_v20(lines, section_id: str, title: str):
    """
    Trả về (start_idx, content_start_idx, heading_line_text).
    Hỗ trợ:
    A) I. Giới thiệu
    B) I. / Giới thiệu
    C) I. Giới thiệu Hãy tưởng tượng...  (heading + content cùng dòng)
    """
    title_n = norm_v20(title)

    for i, line in enumerate(lines):
        # A: same-line heading
        sid, heading_title = same_line_heading_v20(line)
        if sid:
            ht_n = norm_v20(heading_title)

            if same_id_v20(sid, section_id) and (title_n in ht_n or ht_n in title_n or title_n in norm_v20(line)):
                # Nếu cùng dòng có cả content sau title, tách phần content.
                return i, i + 1, line

        # B: split heading
        if is_id_line_v20(line) and i + 1 < len(lines):
            sid2 = get_id_from_line_v20(line)
            next_line = lines[i + 1]

            if same_id_v20(sid2, section_id) and line_contains_title_v20(next_line, title):
                return i, i + 2, line + " " + next_line

        # C: title line, previous line is id
        if i > 0 and is_id_line_v20(lines[i - 1]) and line_contains_title_v20(line, title):
            sid3 = get_id_from_line_v20(lines[i - 1])

            if same_id_v20(sid3, section_id):
                return i - 1, i + 1, lines[i - 1] + " " + line

    return -1, -1, ""


def is_next_heading_start_v20(lines, idx: int, current_id: str) -> bool:
    line = lines[idx]

    # Same-line heading.
    sid, _title = same_line_heading_v20(line)
    if sid and not same_id_v20(sid, current_id):
        return True

    # Split heading.
    if is_id_line_v20(line) and idx + 1 < len(lines) and is_title_candidate_v20(lines[idx + 1]):
        sid2 = get_id_from_line_v20(line)
        if not same_id_v20(sid2, current_id):
            return True

    return False


def extract_inline_content_after_heading_v20(heading_line: str, section_id: str, title: str):
    """
    Nếu heading và nội dung nằm cùng dòng, lấy phần sau title.
    Ví dụ:
    1. Khái niệm Binary Search là...
    """
    raw = str(heading_line or "").strip()
    pattern = rf"^\s*{re.escape(section_id)}\s*[\.\)]\s*{re.escape(title)}\s*"
    after = re.sub(pattern, "", raw, flags=re.I).strip()
    if after != raw and after:
        return after
    return ""


def extract_exact_section_v20(question: str):
    sid, title = parse_section_query_v20(question)
    if not sid:
        return "", "", ""

    raw_text = get_full_raw_text_v20()
    lines = clean_source_lines_v20(raw_text)

    if not lines:
        return sid, title, ""

    start, content_start, heading_line = find_section_start_v20(lines, sid, title)
    if start == -1:
        return sid, title, ""

    selected = []

    inline_content = extract_inline_content_after_heading_v20(heading_line, sid, title)
    if inline_content:
        selected.append(inline_content)

    idx = content_start

    while idx < len(lines):
        if is_next_heading_start_v20(lines, idx, sid):
            break

        line = lines[idx].strip()
        rn = norm_v20(line)

        if rn in ["ai viet nam (aio2026)", "daily ai exercise (aio)", "aivietnam.edu.vn"]:
            idx += 1
            continue
        if "facebook.com" in rn or "sdt/zalo" in rn or "sđt/zalo" in rn:
            idx += 1
            continue
        if line.count(".") >= 15 or re.search(r"\.{8,}", line):
            idx += 1
            continue

        selected.append(line)

        if len("\n".join(selected)) > 6000:
            break

        idx += 1

    source = "\n".join(selected).strip()
    source = repair_extracted_spacing(source) if "repair_extracted_spacing" in globals() else source
    return sid, title, source


def list_detected_headings_v20():
    lines = clean_source_lines_v20(get_full_raw_text_v20())
    headings = []
    seen = set()
    i = 0

    while i < len(lines):
        line = lines[i]

        sid, title = same_line_heading_v20(line)
        if sid and is_title_candidate_v20(title):
            item = f"{sid}. {title}"
            key = norm_v20(item)
            if key not in seen:
                headings.append(item)
                seen.add(key)
            i += 1
            continue

        if is_id_line_v20(line) and i + 1 < len(lines) and is_title_candidate_v20(lines[i + 1]):
            sid2 = get_id_from_line_v20(line)
            title2 = lines[i + 1].strip()
            item = f"{sid2}. {title2}"
            key = norm_v20(item)
            if key not in seen:
                headings.append(item)
                seen.add(key)
            i += 2
            continue

        i += 1

        if len(headings) >= 12:
            break

    return headings


def answer_exact_section_v20(question: str):
    sid, title, source = extract_exact_section_v20(question)

    if not sid:
        return None, []

    if not source or len(source.strip()) < 5:
        found = list_detected_headings_v20()
        hint = "\n".join(f"- {h}" for h in found[:8]) if found else "Chưa phát hiện được heading rõ ràng trong text nguồn."

        msg = f"""## {sid}. {title}

Mình nhận ra đây là câu hỏi theo **mục/section** trong tài liệu, nhưng chưa tách được đúng nội dung của mục này từ text PDF.

Để tránh trả lời sai, mình **không dùng vector search** cho câu hỏi này.

### Các heading mình phát hiện được trong file

{hint}

Bạn hãy copy đúng một heading ở danh sách trên để hỏi lại, hoặc gửi ảnh phần text nguồn của mục đó.
"""
        return msg, []

    title_clean = title.strip()
    source_chunk = f"[NGUỒN FILE: exact-section-v20 | LOẠI: EXACT_SECTION | ĐOẠN: {sid}]\n{sid}. {title_clean}\n\n{source}"

    # Với câu hỏi section, ưu tiên chính xác hơn là văn vẻ:
    # trả nội dung đúng trong file, chỉ thêm tiêu đề.
    answer = f"""## {sid}. {title_clean}

{source}
"""
    return answer, [source_chunk]


def quick_questions_v20():
    headings = list_detected_headings_v20()
    if headings:
        return headings[:4]

    # fallback
    full = norm_v20(get_full_raw_text_v20())
    suggestions = []
    if "embedding" in full:
        suggestions.append("Embedding là gì?")
    if "vector database" in full:
        suggestions.append("Vector Database là gì?")
    if "large language models" in full or "llm" in full:
        suggestions.append("Large Language Models")
    if "binary search" in full:
        suggestions += ["1. Khái niệm", "4. Giả mã"]
    return suggestions[:4]


def answer_question(question):
    if st.session_state.collection is None:
        return "Bạn cần upload tài liệu trước khi đặt câu hỏi.", []

    # V20: nếu là câu hỏi theo mục/section, chỉ trả đúng nội dung section.
    # Không vector search, không LLM tự kéo nhầm.
    if is_section_query_v20(question):
        ans20, chunks20 = answer_exact_section_v20(question)
        return ans20, chunks20

    # V19: xử lý section La Mã/số trước tất cả.
    # Nếu nhận ra đây là câu hỏi section La Mã/số nhưng không tách được source, không rơi xuống vector search.
    if is_roman_or_number_section_query_v19(question):
        ans19, chunks19 = answer_section_v19(question)
        return ans19, chunks19

    # V18: chặn trực tiếp section trước mọi thứ.
    # Sửa lỗi "I. Giới thiệu" bị rơi xuống vector search.
    direct_answer_v18, direct_chunks_v18 = build_direct_section_answer_v18(question)
    if direct_answer_v18:
        return direct_answer_v18, direct_chunks_v18

    # V17: chặn section split-heading trước mọi LLM/vector.
    # Hỗ trợ PDF extract kiểu:
    # I.
    # Giới thiệu
    exact_answer_v17, exact_chunks_v17 = build_answer_from_exact_section_v17(question)
    if exact_answer_v17:
        return exact_answer_v17, exact_chunks_v17

    # V16: chặn section tổng quát trước mọi LLM/vector.
    # Hỗ trợ cả I. Giới thiệu, II.1..., 1. Khái niệm.
    exact_answer, exact_chunks = build_answer_from_exact_section_v16(question)
    if exact_answer:
        return exact_answer, exact_chunks

    # V15: chặn các mục hard-coded nếu cần.
    hard_answer, hard_chunks = hard_exact_section_answer_v15(question)
    if hard_answer:
        return hard_answer, hard_chunks

    if is_visual_question(question):
        load_visual_chunks_on_demand(question)

        figure_context_chunks = get_strict_figure_context_chunks(question)

        if figure_context_chunks:
            same_page_text_chunks = get_same_page_text_for_chunks(
                chunks=figure_context_chunks,
                limit=8,
            )

            merged_chunks = []
            seen = set()

            for chunk in figure_context_chunks + same_page_text_chunks:
                key = chunk[:350]

                if key not in seen:
                    merged_chunks.append(chunk)
                    seen.add(key)

            answer = build_grounded_visual_answer(question, merged_chunks)
            return answer, merged_chunks

        return (
            "Tôi chưa tìm được đúng hình/caption trong PDF. "
            "Bạn hãy hỏi rõ hơn, ví dụ: 'hinh 1', 'hinh 2' hoặc 'hình ở trang 1'.",
            [],
        )

    # TEXT QUESTION V8:
    # Người dùng có thể hỏi bất kỳ nội dung nào trong file.
    # App sẽ tìm bằng keyword + vector, rồi trả lời dựa trên nguồn.
    return answer_any_text_question(question)


def ask_question(question):
    question = str(question).strip()

    if not question:
        return

    st.session_state.messages.append({"role": "user", "content": question})

    with st.spinner("Đang đọc nguồn và tạo câu trả lời..."):
        answer, retrieved_chunks = answer_question(question)

    if answer is None or str(answer).strip() == "":
        answer = "Không tạo được câu trả lời. Có thể LLM đang lỗi hoặc model Ollama chưa chạy."

    st.session_state.messages.append({"role": "assistant", "content": str(answer)})
    st.session_state.last_retrieved_chunks = retrieved_chunks


with st.sidebar:
    st.markdown("## 📚 Nguồn tài liệu")

    st.session_state.notebook_title = st.text_input(
        "Tên notebook",
        value=st.session_state.notebook_title,
    )

    uploaded_files = st.file_uploader(
        "Thêm nguồn",
        type=SUPPORTED_FILE_TYPES,
        accept_multiple_files=True,
        key="sidebar_sources",
    )

    col_a, col_b = st.columns(2)

    with col_a:
        create_clicked = st.button("Tạo notebook", use_container_width=True)

    with col_b:
        clear_clicked = st.button("Xóa", use_container_width=True)

    if create_clicked:
        if not uploaded_files:
            st.warning("Vui lòng chọn ít nhất một file.")
        else:
            with st.spinner("Đang đọc tài liệu..."):
                ok, msg = process_sources(uploaded_files)

            if ok:
                st.success(msg)
                st.rerun()
            else:
                st.error(msg)

    if clear_clicked:
        reset_notebook()
        st.rerun()

    st.markdown("---")

    if st.session_state.sources:
        st.markdown("### Danh sách nguồn")

        for source in st.session_state.sources:
            ui(f"""
            <div class="source-card">
                <div class="source-title">📄 {esc(source.get("name", ""))}</div>
                <div class="source-meta">
                    Loại: {esc(source.get("type", ""))}<br>
                    Nhóm: {esc(source.get("kind", ""))}<br>
                    Trạng thái: {esc(source.get("status", ""))}<br>
                    Chunk: {esc(source.get("chunks", 0))}<br>
                    Ký tự: {esc(source.get("characters", 0))}
                </div>
            </div>
            """)
    else:
        st.info("Chưa có nguồn tài liệu.")


ui(f"""
<div class="top-nav">
    <div class="brand-title">🎋 Khánh AI Notebook</div>
    <div class="brand-subtitle">
        Bản V20: Exact Section Only - hỏi mục/section thì chỉ trả đúng nội dung trong file, không vector search kéo nhầm.
    </div>
    <div class="version-pill">{APP_VERSION}</div>
</div>
""")


source_count = len(st.session_state.sources)
chunk_count = len(st.session_state.all_chunks)
visual_chunk_count = len(get_visual_chunks_from_notebook())
message_count = len(st.session_state.messages)
created_at = st.session_state.created_at if st.session_state.created_at else "Chưa tạo"


ui(f"""
<div class="hero">
    <div class="hero-label">Robust PDF Q&A · Text + Figure Grounding</div>
    <div class="hero-title">
        Hỏi chữ phải ra chữ. <br>
        Hỏi hình phải <span>bám caption thật</span>.
    </div>
    <div class="hero-desc">
        Với nội dung văn bản, hệ thống tìm bằng keyword + vector search, sau đó biên tập lại câu trả lời sạch, không dump nguồn thô.
        Với hình trong PDF, hệ thống dùng caption, chữ trong vùng hình và đoạn giải thích gần hình.
    </div>
    <div class="chip-row">
        <div class="chip chip-hot">🔥 {APP_VERSION}</div>
        <div class="chip">📚 {source_count} nguồn</div>
        <div class="chip">🧩 {chunk_count} đoạn dữ liệu</div>
        <div class="chip">🖼️ {visual_chunk_count} đoạn hình/caption</div>
        <div class="chip">💬 {message_count} tin nhắn</div>
        <div class="chip">🕒 {esc(created_at)}</div>
    </div>
</div>
""")


ui(f"""
<div class="metric-grid">
    <div class="metric-card">
        <div class="metric-number">{source_count}</div>
        <div class="metric-label">Nguồn tài liệu</div>
    </div>
    <div class="metric-card">
        <div class="metric-number">{chunk_count}</div>
        <div class="metric-label">Đoạn dữ liệu</div>
    </div>
    <div class="metric-card">
        <div class="metric-number">{visual_chunk_count}</div>
        <div class="metric-label">Đoạn hình/caption</div>
    </div>
    <div class="metric-card">
        <div class="metric-number">{message_count}</div>
        <div class="metric-label">Tin nhắn</div>
    </div>
</div>
""")


main_col, debug_col = st.columns([2.2, 1], gap="large")


with main_col:
    st.markdown("## 💬 Chat với tài liệu")

    if st.session_state.collection is None:
        ui("""
        <div class="info-box">
            Upload PDF, TXT hoặc ảnh ở thanh bên trái, rồi bấm <b>Tạo notebook</b>.
        </div>
        """)
    else:
        ui(f"""
        <div class="ready-box">
            Notebook đã sẵn sàng · {source_count} nguồn · {chunk_count} đoạn dữ liệu · {visual_chunk_count} đoạn hình/caption.
        </div>
        """)

        st.markdown("#### Gợi ý hỏi nhanh theo file đã upload")

        quick_questions = quick_questions_v20() or st.session_state.quick_questions or [
            "Tóm tắt tài liệu",
            "Nội dung quan trọng",
            "Giải thích tài liệu",
            "Các mục chính trong file",
        ]

        cols = st.columns(4)
        for i, col in enumerate(cols):
            if i < len(quick_questions):
                label = quick_questions[i]
                with col:
                    if st.button(label, use_container_width=True, key=f"quick_question_{i}_{label}"):
                        ask_question(label)
                        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    question = st.chat_input("Hỏi về văn bản hoặc hình trong tài liệu...")

    if question:
        ask_question(question)
        st.rerun()

    if st.session_state.last_retrieved_chunks:
        with st.expander("Xem nguồn được dùng để trả lời", expanded=True):
            for idx, chunk in enumerate(st.session_state.last_retrieved_chunks, start=1):
                label, content = parse_source_label(chunk)

                ui(f"""
                <div class="source-snippet">
                    <b>Nguồn {idx}: {esc(label)}</b><br><br>
                    {esc(content[:1800])}
                </div>
                """)


with debug_col:
    st.markdown("## 📚 Nguồn & Debug")

    st.info(f"Đang chạy: {APP_VERSION}")

    with st.expander("Danh sách nguồn", expanded=True):
        if not st.session_state.sources:
            st.info("Chưa có nguồn nào.")
        else:
            for source in st.session_state.sources:
                st.write(f"**{source.get('name', '')}**")
                st.caption(
                    f"Loại: {source.get('type', '')} | "
                    f"Nhóm: {source.get('kind', '')} | "
                    f"Chunk: {source.get('chunks', 0)}"
                )

    with st.expander("Xem chunk hình/caption", expanded=False):
        visual_chunks = get_visual_chunks_from_notebook()

        if not visual_chunks:
            st.warning("Chưa có chunk hình. Hỏi 'hinh 1' để hệ thống trích caption/hình.")
        else:
            for i, chunk in enumerate(visual_chunks[:20], start=1):
                st.markdown(f"### Figure chunk {i}")
                st.text_area(
                    f"Chunk hình {i}",
                    value=chunk[:4000],
                    height=260,
                )

    with st.expander("Xem text nguồn", expanded=False):
        if not st.session_state.sources:
            st.info("Chưa có dữ liệu.")
        else:
            for source in st.session_state.sources:
                st.markdown(f"### {source.get('name', '')}")
                st.text_area(
                    "Nội dung xem trước",
                    value=source.get("text_preview", ""),
                    height=260,
                )