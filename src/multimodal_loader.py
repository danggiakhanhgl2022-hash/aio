import os
import tempfile
import base64

import pypdf
import cv2
import ollama
from faster_whisper import WhisperModel

try:
    import fitz  # PyMuPDF
except ImportError:
    fitz = None

from src.config import (
    LLM_MODEL,
    VISION_MODEL,
    MAX_PDF_VISION_PAGES,
    MAX_VIDEO_FRAMES,
    MAX_FILE_SIZE_MB
)


# =========================
# FILE UTILS
# =========================

def save_uploaded_file(uploaded_file, suffix):
    """
    Lưu file upload từ Streamlit thành file tạm.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


def safe_delete(path):
    """
    Xóa file tạm an toàn.
    """
    try:
        if path and os.path.exists(path):
            os.unlink(path)
    except Exception:
        pass


def clean_text(text):
    """
    Làm sạch text sau khi trích xuất.
    """
    if not text:
        return ""

    text = text.replace("\x00", " ")
    text = text.replace("\r", "\n")

    lines = []
    for line in text.split("\n"):
        line = line.strip()
        if line:
            lines.append(line)

    return "\n".join(lines)


# =========================
# NORMALIZE VISION OUTPUT
# =========================

def normalize_vision_output_to_vietnamese(text):
    """
    Chuẩn hóa output của vision model sang tiếng Việt.
    Dùng để sửa lỗi model vision trả lẫn tiếng Trung/Anh.
    """
    if not text or not text.strip():
        return ""

    prompt = f"""
Bạn là hệ thống biên tập ngôn ngữ.

Hãy viết lại nội dung sau HOÀN TOÀN bằng TIẾNG VIỆT.

YÊU CẦU BẮT BUỘC:
- Không được dùng tiếng Trung.
- Không được dùng tiếng Nhật.
- Không được dùng tiếng Anh trừ các nhãn kỹ thuật bắt buộc như: File Document, Vector Database, Search, Retriever, Question, Prompt, Vicuna LLM, Answer, Output.
- Dịch toàn bộ phần tiếng Trung hoặc ngôn ngữ khác sang tiếng Việt.
- Không thêm thông tin mới.
- Không bịa thêm.
- Giữ cấu trúc đánh số 1, 2, 3, 4, 5 nếu có.
- Viết rõ ràng, dễ hiểu.

Nội dung cần viết lại:
{text}
"""

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            options={"temperature": 0}
        )

        result = response.get("message", {}).get("content", "")

        if result and result.strip():
            return clean_text(result)

        return text

    except Exception:
        return text


# =========================
# PDF TEXT
# =========================

def read_pdf_text_with_pypdf(path):
    """
    Đọc text thật trong PDF bằng pypdf.
    Phù hợp với PDF xuất từ Word, Google Docs, slide, LaTeX.
    """
    try:
        reader = pypdf.PdfReader(path)
        pages_text = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)

        return clean_text("\n".join(pages_text))

    except Exception as e:
        return f"[PDF TEXT ERROR] {e}"


# =========================
# IMAGE / VISION
# =========================

def image_path_to_text(image_path):
    """
    Đọc/mô tả ảnh bằng vision model Ollama.
    Có 3 cách gọi để tăng khả năng chạy với nhiều vision model khác nhau.
    """

    prompt = """
Bạn là hệ thống đọc hiểu hình ảnh chính xác.

NHIỆM VỤ:
Phân tích ảnh này và trả lời bằng TIẾNG VIỆT.

QUY TẮC BẮT BUỘC:
- Chỉ mô tả những gì thật sự nhìn thấy trong ảnh.
- Không tự suy luận thêm nội dung ngoài ảnh.
- Không đổi nghĩa nội dung trong ảnh.
- Nếu ảnh là sơ đồ, hãy đọc đúng các nhãn và mô tả đúng mũi tên.
- Nếu ảnh là ảnh chụp màn hình, slide, tài liệu học tập, bảng hoặc biểu đồ, hãy đọc các chữ quan trọng.
- Nếu có chữ tiếng Anh như File Document, Vector Database, Search, Retriever, Question, Prompt, Vicuna LLM, Answer, Output thì được giữ nguyên.
- Nếu xuất hiện tiếng Trung hoặc ngôn ngữ khác trong kết quả, phải dịch sang tiếng Việt.
- Không được trả lời bằng tiếng Trung.
- Không được xen tiếng Trung.
- Nếu không chắc chữ nào, hãy ghi "không rõ".
- Với sơ đồ RAG, hãy hiểu là quy trình hỏi đáp / tạo câu trả lời từ tài liệu, không phải tạo câu hỏi.

TRẢ LỜI THEO CẤU TRÚC:
1. Loại ảnh:
2. Chữ/nhãn nhìn thấy trong ảnh:
3. Các thành phần chính:
4. Luồng xử lý trong ảnh:
5. Tóm tắt ngắn gọn:
"""

    errors = []

    try:
        with open(image_path, "rb") as image_file:
            image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
    except Exception as e:
        return f"[VISION ERROR] Không đọc được file ảnh: {e}"

    # Cách 1: ollama.chat với base64
    try:
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_base64],
                }
            ],
            options={"temperature": 0}
        )

        content = response.get("message", {}).get("content", "")

        if content and content.strip():
            content = clean_text(content)
            content = normalize_vision_output_to_vietnamese(content)
            return content

        errors.append("Cách 1 trả về rỗng.")

    except Exception as e:
        errors.append(f"Cách 1 lỗi: {e}")

    # Cách 2: ollama.generate với base64
    try:
        response = ollama.generate(
            model=VISION_MODEL,
            prompt=prompt,
            images=[image_base64],
            options={"temperature": 0}
        )

        content = response.get("response", "")

        if content and content.strip():
            content = clean_text(content)
            content = normalize_vision_output_to_vietnamese(content)
            return content

        errors.append("Cách 2 trả về rỗng.")

    except Exception as e:
        errors.append(f"Cách 2 lỗi: {e}")

    # Cách 3: ollama.chat với đường dẫn file
    try:
        response = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [image_path],
                }
            ],
            options={"temperature": 0}
        )

        content = response.get("message", {}).get("content", "")

        if content and content.strip():
            content = clean_text(content)
            content = normalize_vision_output_to_vietnamese(content)
            return content

        errors.append("Cách 3 trả về rỗng.")

    except Exception as e:
        errors.append(f"Cách 3 lỗi: {e}")

    return "[VISION ERROR] Không thể xử lý ảnh.\n" + "\n".join(errors)


# =========================
# PDF SCAN / PDF IMAGE
# =========================

def read_pdf_by_rendering_pages(path, max_pages=MAX_PDF_VISION_PAGES):
    """
    Nếu PDF là scan hoặc ít text, chuyển từng trang thành ảnh rồi dùng vision model.
    """
    if fitz is None:
        return "[PDF VISION ERROR] Máy chưa cài PyMuPDF."

    texts = []

    try:
        doc = fitz.open(path)
        total_pages = len(doc)
        pages_to_process = min(total_pages, max_pages)

        for page_index in range(pages_to_process):
            page = doc[page_index]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))

            img_path = tempfile.NamedTemporaryFile(delete=False, suffix=".png").name
            pix.save(img_path)

            page_text = image_path_to_text(img_path)
            texts.append(f"--- Trang {page_index + 1} ---\n{page_text}")

            safe_delete(img_path)

        doc.close()

        if total_pages > max_pages:
            texts.append(
                f"[Lưu ý] PDF có {total_pages} trang, app chỉ xử lý {max_pages} trang đầu."
            )

        return clean_text("\n\n".join(texts))

    except Exception as e:
        return f"[PDF VISION ERROR] {e}"


def read_pdf_file(uploaded_file):
    """
    Xử lý PDF:
    - Ưu tiên đọc text bằng pypdf.
    - Nếu PDF scan hoặc ít text thì render trang thành ảnh và dùng vision model.
    """
    path = save_uploaded_file(uploaded_file, ".pdf")

    try:
        text = read_pdf_text_with_pypdf(path)

        if text and not text.startswith("[PDF TEXT ERROR]") and len(text.strip()) >= 300:
            return "PDF Text", text

        vision_text = read_pdf_by_rendering_pages(path)

        combined = ""

        if text and not text.startswith("[PDF TEXT ERROR]"):
            combined += "PHẦN TEXT ĐỌC BẰNG PYPDF:\n"
            combined += text
            combined += "\n\n"

        combined += "PHẦN TRÍCH XUẤT TỪ ẢNH PDF:\n"
        combined += vision_text

        return "PDF Scan / PDF Image", clean_text(combined)

    finally:
        safe_delete(path)


# =========================
# TXT
# =========================

def read_txt_file(uploaded_file):
    """
    Đọc file TXT.
    """
    raw = uploaded_file.getvalue()

    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            text = raw.decode("latin-1")
        except Exception as e:
            return "Text", f"[TXT ERROR] {e}"

    return "Text", clean_text(text)


# =========================
# IMAGE FILE
# =========================

def read_image_file(uploaded_file):
    """
    Xử lý ảnh: png, jpg, jpeg, webp.
    """
    suffix = os.path.splitext(uploaded_file.name)[1] or ".png"
    path = save_uploaded_file(uploaded_file, suffix)

    try:
        text = image_path_to_text(path)
        return "Image", clean_text(text)

    finally:
        safe_delete(path)


# =========================
# AUDIO
# =========================

def read_audio_file(uploaded_file):
    """
    Xử lý audio bằng faster-whisper.
    """
    suffix = os.path.splitext(uploaded_file.name)[1] or ".mp3"
    path = save_uploaded_file(uploaded_file, suffix)

    try:
        model = WhisperModel("base", device="cpu", compute_type="int8")
        segments, info = model.transcribe(path)

        transcript_parts = []

        for segment in segments:
            transcript_parts.append(segment.text)

        transcript = " ".join(transcript_parts)

        return "Audio", clean_text(transcript)

    except Exception as e:
        return "Audio", f"[AUDIO ERROR] {e}"

    finally:
        safe_delete(path)


# =========================
# VIDEO
# =========================

def read_video_file(uploaded_file, max_frames=MAX_VIDEO_FRAMES):
    """
    Xử lý video:
    - Lấy một số frame đại diện.
    - Dùng vision model mô tả từng frame.
    """
    suffix = os.path.splitext(uploaded_file.name)[1] or ".mp4"
    video_path = save_uploaded_file(uploaded_file, suffix)

    descriptions = []

    try:
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            return "Video", "[VIDEO ERROR] Không thể mở video."

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames <= 0:
            cap.release()
            return "Video", "[VIDEO ERROR] Video không có frame hợp lệ."

        if total_frames <= max_frames:
            positions = list(range(total_frames))
        else:
            step = max(total_frames // max_frames, 1)
            positions = [i * step for i in range(max_frames)]

        for idx, frame_no in enumerate(positions):
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_no)
            success, frame = cap.read()

            if not success:
                continue

            frame_path = tempfile.NamedTemporaryFile(delete=False, suffix=".jpg").name
            cv2.imwrite(frame_path, frame)

            frame_text = image_path_to_text(frame_path)
            descriptions.append(f"--- Frame {idx + 1} ---\n{frame_text}")

            safe_delete(frame_path)

        cap.release()

        if not descriptions:
            return "Video", "[VIDEO ERROR] Không trích xuất được frame nào."

        return "Video", clean_text("\n\n".join(descriptions))

    except Exception as e:
        return "Video", f"[VIDEO ERROR] {e}"

    finally:
        safe_delete(video_path)


# =========================
# MAIN EXTRACTOR
# =========================

def extract_text_from_file(uploaded_file):
    """
    Hàm tổng xử lý mọi file upload.

    Trả về:
    - file_type
    - text đã trích xuất
    - status_message
    """

    if uploaded_file is None:
        return "None", "", "Chưa có file."

    file_name = uploaded_file.name.lower()
    file_size_mb = uploaded_file.size / (1024 * 1024)

    if file_size_mb > MAX_FILE_SIZE_MB:
        return "Too Large", "", f"File quá lớn. Vui lòng chọn file nhỏ hơn {MAX_FILE_SIZE_MB}MB."

    try:
        if file_name.endswith(".pdf"):
            file_type, text = read_pdf_file(uploaded_file)

        elif file_name.endswith(".txt"):
            file_type, text = read_txt_file(uploaded_file)

        elif file_name.endswith((".png", ".jpg", ".jpeg", ".webp")):
            file_type, text = read_image_file(uploaded_file)

        elif file_name.endswith((".mp3", ".wav", ".m4a")):
            file_type, text = read_audio_file(uploaded_file)

        elif file_name.endswith((".mp4", ".mov", ".avi", ".mkv")):
            file_type, text = read_video_file(uploaded_file)

        else:
            return "Unsupported", "", "Định dạng file chưa được hỗ trợ."

        text = clean_text(text)

        if (
            text.startswith("[VISION ERROR]")
            or text.startswith("[PDF")
            or text.startswith("[AUDIO ERROR]")
            or text.startswith("[VIDEO ERROR]")
            or text.startswith("[TXT ERROR]")
        ):
            return file_type, text, text

        if not text.strip():
            return file_type, "", "Không trích xuất được nội dung từ file."

        if len(text.strip()) < 20:
            return file_type, text, "Nội dung trích xuất được khá ngắn, nhưng vẫn có thể thử hỏi đáp."

        return file_type, text, "Xử lý file thành công."

    except Exception as e:
        return "Error", "", f"Lỗi khi xử lý file: {e}"