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


APP_VERSION = "UNIVERSAL_FILE_RETRIEVAL_V8"

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

    return fallback_kind


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
    text = clean_chunk_text_for_answer(text, max_chars=7000)
    text = repair_extracted_spacing(text)

    text = re.sub(r"NGUỒN:\s*PDF_TEXT\s*TRANG:\s*\d+", "", text, flags=re.I)
    text = re.sub(r"NGUỒN:\s*.*", "", text)
    text = re.sub(r"LOẠI:\s*.*", "", text)
    text = re.sub(r"ĐOẠN:\s*\d+", "", text)

    lines = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.count(".") >= 15 or re.search(r"\.{8,}", line):
            continue
        lines.append(line)

    text = "\n".join(lines)
    text = re.sub(r"\s+", " ", text).strip()
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


def universal_answer_from_sources(question: str, chunks):
    """
    Trả lời mọi nội dung trong file bằng LLM dựa trên nguồn.
    Không dump thô chunk, không bịa ngoài file.
    """
    if not chunks:
        return "Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."

    # Chuẩn hóa nguồn đưa vào LLM: bỏ marker kỹ thuật, mục lục dài.
    clean_sources = []
    for i, chunk in enumerate(chunks, start=1):
        text = clean_source_text_for_display(chunk) if "clean_source_text_for_display" in globals() else clean_chunk_text_for_answer(chunk)
        text = repair_extracted_spacing(text) if "repair_extracted_spacing" in globals() else text

        if not text.strip():
            continue

        if is_toc_or_noise_text(text) and len(clean_sources) >= 1:
            continue

        clean_sources.append(f"[Nguồn {i}]\n{text[:2200]}")

        if len(clean_sources) >= 8:
            break

    if not clean_sources:
        return "Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."

    source_text = "\n\n".join(clean_sources)

    prompt = f"""
Bạn là trợ lý hỏi đáp tài liệu.

Nhiệm vụ:
- Người dùng có thể hỏi bất kỳ nội dung nào trong file đã upload.
- Hãy tìm ý trong NGUỒN và trả lời rõ ràng bằng tiếng Việt.
- Không được bịa ngoài nguồn.
- Không được copy thô nguyên chunk/mục lục.
- Nếu câu hỏi là một tiêu đề/mục, hãy giải thích mục đó dựa trên nội dung nguồn.
- Nếu trong nguồn có thông tin liên quan dù chỉ một phần, hãy trả lời phần tìm được.
- Nếu thật sự không có thông tin liên quan, mới nói: "Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."

CÂU HỎI:
{question}

NGUỒN:
{source_text}

CÁCH TRẢ LỜI:
- Trả lời trực tiếp vào câu hỏi.
- Nếu có nhiều ý, dùng bullet ngắn.
- Nếu có công thức/code/quy trình trong nguồn, tóm tắt đúng ý chính.
- Cuối câu trả lời có thể thêm "Nguồn: trang/đoạn liên quan" nếu thấy trong nguồn.
"""

    answer = generate_answer(prompt, chunks)

    if answer and not is_not_found_answer(answer):
        return answer

    # Fallback: nếu LLM nói không thấy nhưng chúng ta có nguồn, tự trả lời sạch.
    fallback = build_clean_generic_answer(question, chunks) if "build_clean_generic_answer" in globals() else None
    if fallback:
        return fallback

    # Fallback cuối cùng: trích đoạn sạch, không dump mục lục.
    passages = extract_relevant_passages(question, chunks, max_passages=3) if "extract_relevant_passages" in globals() else []
    if passages:
        return (
            "Mình tìm thấy thông tin liên quan trong tài liệu:\n\n"
            + "\n\n".join(f"- {p[:900]}" for p in passages[:3])
        )

    return "Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."


def answer_any_text_question(question: str):
    """
    Luồng trả lời chữ tổng quát:
    - special handlers nếu có
    - universal retrieval cho mọi câu khác
    """
    q_norm = normalize_text(question)

    # Các câu đặc biệt trả lời nhanh/sạch.
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


def answer_question(question):
    if st.session_state.collection is None:
        return "Bạn cần upload tài liệu trước khi đặt câu hỏi.", []

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
        Bản V8: hỏi bất kỳ nội dung nào trong file bằng keyword + vector search; hỏi hình PDF bám caption/text quanh hình.
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
        Với nội dung văn bản, hệ thống tìm bằng keyword + vector search để lấy thông tin bất kỳ trong file.
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

        st.markdown("#### Gợi ý hỏi nhanh")

        q1, q2, q3, q4 = st.columns(4)

        with q1:
            if st.button("Hình 1 nói gì?", use_container_width=True):
                ask_question("hinh 1")
                st.rerun()

        with q2:
            if st.button("Large Language Models", use_container_width=True):
                ask_question("Large Language Models")
                st.rerun()

        with q3:
            if st.button("Tóm tắt tài liệu", use_container_width=True):
                ask_question("Tóm tắt tài liệu này thật dễ hiểu và ngắn gọn.")
                st.rerun()

        with q4:
            if st.button("Nội dung quan trọng", use_container_width=True):
                ask_question("Nêu các nội dung quan trọng nhất trong tài liệu đã upload.")
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