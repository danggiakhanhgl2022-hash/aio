import os
import re
import base64
import unicodedata
from io import BytesIO

try:
    import ollama
except Exception:
    ollama = None

from pypdf import PdfReader

try:
    import fitz  # PyMuPDF
except Exception:
    fitz = None


VISION_MODELS = ["llava:latest", "moondream:latest"]


def normalize_no_accent(text: str) -> str:
    if not text:
        return ""

    text = str(text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return text.lower().strip()


def get_file_name(uploaded_file):
    return getattr(uploaded_file, "name", "uploaded_file")


def get_file_extension(uploaded_file):
    return get_file_name(uploaded_file).lower().split(".")[-1]


def read_uploaded_bytes(uploaded_file):
    if hasattr(uploaded_file, "getvalue"):
        return uploaded_file.getvalue()

    uploaded_file.seek(0)
    data = uploaded_file.read()
    uploaded_file.seek(0)
    return data


def clean_extracted_text(text: str) -> str:
    if not text:
        return ""

    lines = text.splitlines()
    cleaned_lines = []

    for line in lines:
        line = line.strip()

        if not line:
            continue

        if len(line) < 2:
            continue

        # Không bỏ số trang hoàn toàn nếu dòng có ý nghĩa khác.
        cleaned_lines.append(line)

    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r"\n{3,}", "\n\n", cleaned_text)
    cleaned_text = re.sub(r"[ \t]+", " ", cleaned_text)

    return cleaned_text.strip()


def read_pdf_text_pages(file_bytes):
    pages = []

    # Ưu tiên PyMuPDF vì giữ trang và layout tốt hơn.
    if fitz is not None:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")

            for i in range(len(doc)):
                page = doc.load_page(i)
                text = page.get_text("text") or ""
                text = clean_extracted_text(text)

                if text.strip():
                    pages.append(
                        f"""
==============================
NGUỒN: PDF_TEXT
TRANG: {i + 1}
==============================
{text}
"""
                    )

            if pages:
                return pages

        except Exception:
            pass

    # Fallback pypdf
    try:
        reader = PdfReader(BytesIO(file_bytes))

        for i, page in enumerate(reader.pages, start=1):
            page_text = page.extract_text() or ""
            page_text = clean_extracted_text(page_text)

            if page_text.strip():
                pages.append(
                    f"""
==============================
NGUỒN: PDF_TEXT
TRANG: {i}
==============================
{page_text}
"""
                )
    except Exception:
        pass

    return pages


def read_pdf_text_only(uploaded_file):
    file_bytes = read_uploaded_bytes(uploaded_file)
    text_sections = read_pdf_text_pages(file_bytes)

    if text_sections:
        return "\n\n".join(text_sections).strip()

    if fitz is not None:
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            fallback_sections = []

            for page in range(1, len(doc) + 1):
                fallback_sections.append(
                    f"""
==============================
NGUỒN: PDF_TEXT
TRANG: {page}
==============================
Trang {page} không trích xuất được chữ trực tiếp. Có thể đây là PDF scan hoặc nội dung nằm trong ảnh.
"""
                )

            return "\n\n".join(fallback_sections).strip()

        except Exception:
            return ""

    return ""


def get_page_lines(page):
    data = page.get_text("dict")
    lines = []

    for block in data.get("blocks", []):
        if block.get("type") != 0:
            continue

        for line in block.get("lines", []):
            spans = line.get("spans", [])
            text = " ".join(span.get("text", "") for span in spans).strip()

            if not text:
                continue

            bbox = line.get("bbox")

            if bbox:
                lines.append(
                    {
                        "text": text,
                        "norm": normalize_no_accent(text),
                        "bbox": fitz.Rect(bbox),
                    }
                )

    return lines


def find_real_figure_caption_candidates(file_bytes, figure_number):
    if fitz is None:
        raise RuntimeError("Chưa cài PyMuPDF. Hãy chạy: pip install pymupdf")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    candidates = []

    # chấp nhận Hình/hinh/Figure/Fig
    caption_regex = re.compile(
        rf"^\s*(hinh|hình|figure|fig)\.?\s*{figure_number}\b",
        re.IGNORECASE,
    )

    for page_index in range(len(doc)):
        page = doc.load_page(page_index)
        lines = get_page_lines(page)

        for line in lines:
            raw = line["text"].strip()
            norm = line["norm"]

            if not caption_regex.search(norm):
                continue

            score = 100

            if ":" in raw or "-" in raw or "–" in raw:
                score += 50

            after = re.sub(
                rf"^\s*(hinh|hình|figure|fig)\.?\s*{figure_number}\b",
                "",
                norm,
                flags=re.IGNORECASE,
            ).strip()

            if len(after) >= 8:
                score += 40

            # Mục lục thường có nhiều dấu chấm.
            if raw.count(".") >= 4:
                score -= 120

            if len(raw) < 8:
                score -= 30

            candidates.append(
                {
                    "page_index": page_index,
                    "page_number": page_index + 1,
                    "caption_text": raw,
                    "caption_rect": line["bbox"],
                    "score": score,
                }
            )

    candidates.sort(key=lambda x: x["score"], reverse=True)
    return candidates


def extract_text_around_figure(file_bytes, figure_number):
    """
    Dùng cho PDF có chữ thật.
    Không dùng vision để trả lời hình; chỉ lấy caption + chữ trong vùng hình + đoạn giải thích gần hình.
    """
    if fitz is None:
        raise RuntimeError("Chưa cài PyMuPDF. Hãy chạy: pip install pymupdf")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    candidates = find_real_figure_caption_candidates(file_bytes, figure_number)

    if not candidates:
        return []

    best = candidates[0]
    page = doc.load_page(best["page_index"])
    page_rect = page.rect
    caption_rect = best["caption_rect"]

    # Vùng hình nằm phía trên caption.
    figure_top = max(0, caption_rect.y0 - page_rect.height * 0.50)
    figure_bottom = min(page_rect.height, caption_rect.y1 + 24)
    figure_rect = fitz.Rect(0, figure_top, page_rect.width, figure_bottom)
    figure_text = clean_extracted_text(page.get_textbox(figure_rect))

    # Vùng giải thích nằm dưới caption.
    after_top = min(page_rect.height, caption_rect.y1 + 12)
    after_bottom = page_rect.height
    after_rect = fitz.Rect(0, after_top, page_rect.width, after_bottom)
    after_text = clean_extracted_text(page.get_textbox(after_rect))

    # Lấy thêm đầu trang sau vì nhiều PDF giải thích tiếp sang trang sau.
    next_page_text = ""
    if best["page_index"] + 1 < len(doc):
        next_page = doc.load_page(best["page_index"] + 1)
        next_rect = fitz.Rect(0, 0, next_page.rect.width, next_page.rect.height * 0.50)
        next_page_text = clean_extracted_text(next_page.get_textbox(next_rect))

    return [
        {
            "figure_number": figure_number,
            "page_number": best["page_number"],
            "caption_text": best["caption_text"],
            "figure_text": figure_text,
            "after_text": after_text,
            "next_page_text": next_page_text,
        }
    ]


def analyze_pdf_figures_with_vision(file_bytes, file_name, figure_numbers):
    """
    Giữ tên hàm cũ để app không lỗi.
    Thực tế hàm này KHÔNG dùng vision để trả lời PDF nữa.
    """
    sections = []

    for figure_number in figure_numbers:
        try:
            contexts = extract_text_around_figure(file_bytes, figure_number)

            if not contexts:
                sections.append(
                    f"""
==============================
NGUỒN: PDF_FIGURE_CONTEXT_ERROR
FILE: {file_name}
HÌNH: {figure_number}
==============================
Không tìm thấy caption thật của Hình {figure_number} trong PDF.
"""
                )
                continue

            for item in contexts:
                sections.append(
                    f"""
==============================
NGUỒN: PDF_FIGURE_CONTEXT
FILE: {file_name}
HÌNH: {item["figure_number"]}
TRANG: {item["page_number"]}
CAPTION: {item["caption_text"]}
==============================
CHỮ TRONG VÙNG HÌNH:
{item["figure_text"]}

ĐOẠN GIẢI THÍCH NGAY DƯỚI / GẦN HÌNH:
{item["after_text"]}

ĐOẠN ĐẦU TRANG SAU NẾU CÓ:
{item["next_page_text"]}
"""
                )

        except Exception as e:
            sections.append(
                f"""
==============================
NGUỒN: PDF_FIGURE_CONTEXT_ERROR
FILE: {file_name}
HÌNH: {figure_number}
==============================
Lỗi khi trích nội dung Hình {figure_number}:
{e}
"""
            )

    return "\n\n".join(sections).strip()


def get_ollama_content(response):
    if isinstance(response, dict):
        return response.get("message", {}).get("content", "")

    if hasattr(response, "message"):
        message = response.message

        if hasattr(message, "content"):
            return message.content

    return ""


def read_image_bytes_with_vision(image_bytes):
    """
    Chỉ dùng cho file ảnh upload riêng hoặc fallback theo trang.
    """
    if ollama is None:
        return "", "", "Chưa cài hoặc chưa import được ollama."

    prompt = """
Bạn chỉ mô tả đúng những gì nhìn thấy trong ảnh.
Không bịa. Không suy luận ngoài ảnh.
Trả lời bằng tiếng Việt.
"""

    image_base64 = base64.b64encode(image_bytes).decode("utf-8")
    errors = []

    for model in VISION_MODELS:
        try:
            response = ollama.chat(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                        "images": [image_base64],
                    }
                ],
                options={"temperature": 0},
            )

            content = get_ollama_content(response).strip()

            if content:
                return content, model, ""

        except Exception as e:
            errors.append(f"{model}: {e}")

    return "", "", "\n".join(errors)


def render_pdf_page_to_png_bytes(file_bytes, page_number, dpi=220):
    if fitz is None:
        raise RuntimeError("Chưa cài PyMuPDF. Hãy chạy: pip install pymupdf")

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    page_index = page_number - 1

    if page_index < 0 or page_index >= len(doc):
        raise ValueError(f"PDF không có trang {page_number}")

    page = doc.load_page(page_index)
    zoom = dpi / 72
    matrix = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    return pix.tobytes("png")


def analyze_pdf_pages_with_vision(file_bytes, file_name, page_numbers):
    sections = []

    for page_number in page_numbers:
        try:
            png_bytes = render_pdf_page_to_png_bytes(file_bytes, page_number, 220)
            vision_text, model_used, error = read_image_bytes_with_vision(png_bytes)

            if vision_text:
                sections.append(
                    f"""
==============================
NGUỒN: PDF_PAGE_IMAGE_FALLBACK
FILE: {file_name}
TRANG: {page_number}
MODEL: {model_used}
==============================
{vision_text}
"""
                )
            else:
                sections.append(
                    f"""
==============================
NGUỒN: PDF_PAGE_IMAGE_ERROR
FILE: {file_name}
TRANG: {page_number}
==============================
Không đọc được trang bằng vision.
Lỗi:
{error}
"""
                )

        except Exception as e:
            sections.append(
                f"""
==============================
NGUỒN: PDF_PAGE_IMAGE_ERROR
FILE: {file_name}
TRANG: {page_number}
==============================
Lỗi:
{e}
"""
            )

    return "\n\n".join(sections).strip()


def read_txt_text(uploaded_file):
    file_bytes = read_uploaded_bytes(uploaded_file)
    encodings = ["utf-8-sig", "utf-8", "cp1258", "latin-1"]

    for enc in encodings:
        try:
            return file_bytes.decode(enc).strip()
        except Exception:
            continue

    return file_bytes.decode("utf-8", errors="ignore").strip()


def read_image_text(uploaded_file):
    image_bytes = read_uploaded_bytes(uploaded_file)
    text, model_used, error = read_image_bytes_with_vision(image_bytes)

    if text:
        return text, f"Xử lý ảnh thành công bằng model {model_used}."

    return f"[VISION ERROR] Không đọc được ảnh bằng vision model.\n{error}", "Không xử lý được ảnh."


def extract_text_from_file(uploaded_file):
    ext = get_file_extension(uploaded_file)

    try:
        if ext == "pdf":
            text = read_pdf_text_only(uploaded_file)

            if text.strip():
                return "PDF Text", text, "Đã xử lý PDF: đọc chữ trước. Hình sẽ trích caption/text khi người dùng hỏi."

            return "PDF", "", "Không trích xuất được nội dung từ PDF."

        if ext == "txt":
            text = read_txt_text(uploaded_file)

            if text.strip():
                return "TXT Text", text, "Xử lý TXT thành công."

            return "TXT Text", "", "Không đọc được TXT."

        if ext in ["png", "jpg", "jpeg", "webp"]:
            text, status = read_image_text(uploaded_file)
            return "Image", text, status

        return "Unknown", "", f"Chưa hỗ trợ định dạng file: {ext}"

    except Exception as e:
        return "Error", "", f"Lỗi khi xử lý file: {e}"