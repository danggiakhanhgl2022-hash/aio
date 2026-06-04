import os
import tempfile

import pypdf
import fitz  # pymupdf
import cv2
import ollama
from faster_whisper import WhisperModel


VISION_MODEL = "llama3.2-vision"


def save_uploaded_file(uploaded_file, suffix):
    """
    Lưu file upload từ Streamlit thành file tạm.
    """
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(uploaded_file.getvalue())
        return tmp.name


def safe_delete(path):
    """
    Xóa file tạm, tránh lỗi nếu file không tồn tại.
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


def read_pdf_text_with_pypdf(path):
    """
    Đọc text thật trong PDF bằng pypdf.
    Phù hợp với PDF xuất từ Word, Google Docs, LaTeX.
    """
    try:
        reader = pypdf.PdfReader(path)
        pages_text = []

        for page in reader.pages:
            page_text = page.extract_text() or ""
            pages_text.append(page_text)

        return clean_text("\n".join(pages_text))
    except Exception:
        return ""


def image_path_to_text(image_path):
    """
    Dùng Ollama vision model để mô tả ảnh thành text.
    Có thể xử lý ảnh, biểu đồ, sơ đồ, ảnh chụp tài liệu.
    """
    prompt = """
Bạn là hệ thống trích xuất thông tin từ hình ảnh.

Yêu cầu:
1. Nếu ảnh có chữ, hãy đọc lại chữ quan trọng.
2. Nếu ảnh có bảng, hãy mô tả nội dung bảng.
3. Nếu ảnh có biểu đồ/sơ đồ, hãy giải thích ý nghĩa chính.
4. Nếu ảnh là ảnh chụp tài liệu, hãy tóm tắt nội dung.
5. Trả lời bằng tiếng Việt, rõ ràng, có cấu trúc.
"""

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
        )

        return response["message"]["content"]
    except Exception as e:
        return f"[Không thể xử lý ảnh bằng vision model: {e}]"


def read_pdf_by_rendering_pages(path, max_pages=8):
    """
    Fallback cho PDF scan hoặc PDF nhiều hình:
    chuyển từng trang PDF thành ảnh rồi dùng vision model đọc/mô tả.

    max_pages để tránh file quá dài làm xử lý quá lâu.
    """
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
            texts.append(f"--- Nội dung trích xuất từ trang {page_index + 1} ---\n{page_text}")

            safe_delete(img_path)

        doc.close()

        if total_pages > max_pages:
            texts.append(
                f"\n[Lưu ý: PDF có {total_pages} trang. App chỉ xử lý vision {max_pages} trang đầu để tránh quá tải.]"
            )

        return clean_text("\n\n".join(texts))

    except Exception as e:
        return f"[Không thể render PDF thành ảnh: {e}]"


def read_pdf_file(uploaded_file):
    """
    Xử lý PDF toàn diện:
    - Ưu tiên đọc text thật bằng pypdf.
    - Nếu text quá ít, fallback sang vision/OCR bằng cách render trang PDF thành ảnh.
    """
    path = save_uploaded_file(uploaded_file, ".pdf")

    try:
        text = read_pdf_text_with_pypdf(path)

        # Nếu PDF đọc được đủ text thì dùng luôn
        if len(text.strip()) >= 300:
            return "PDF Text", text

        # Nếu PDF scan hoặc text quá ít thì fallback sang vision
        vision_text = read_pdf_by_rendering_pages(path)

        combined = ""
        if text.strip():
            combined += "PHẦN TEXT ĐỌC BẰNG PYPDF:\n" + text + "\n\n"

        combined += "PHẦN TRÍCH XUẤT TỪ HÌNH ẢNH/TRANG PDF:\n" + vision_text

        return "PDF Scan / PDF Image", clean_text(combined)

    finally:
        safe_delete(path)


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
        except Exception:
            text = ""

    return "Text", clean_text(text)


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
        return "Audio", f"[Không thể chuyển âm thanh thành text: {e}]"

    finally:
        safe_delete(path)


def extract_audio_from_video(video_path):
    """
    Tách audio từ video bằng OpenCV là hạn chế, nên hàm này hiện chưa tách audio trực tiếp.
    App sẽ xử lý video bằng frame trước.
    """
    return ""


def read_video_file(uploaded_file, max_frames=6):
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
            return "Video", "Không thể mở video."

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        if total_frames <= 0:
            cap.release()
            return "Video", "Video không có frame hợp lệ."

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
            descriptions.append(
                f"--- Frame {idx + 1} của video ---\n{frame_text}"
            )

            safe_delete(frame_path)

        cap.release()

        if not descriptions:
            return "Video", "Không trích xuất được frame nào từ video."

        return "Video", clean_text("\n\n".join(descriptions))

    except Exception as e:
        return "Video", f"[Không thể xử lý video: {e}]"

    finally:
        safe_delete(video_path)


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

    # Giới hạn dung lượng để app không bị đứng
    if file_size_mb > 200:
        return "Too Large", "", "File quá lớn. Vui lòng chọn file nhỏ hơn 200MB."

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

        if not text.strip():
            return file_type, "", "Không trích xuất được nội dung từ file."

        if len(text.strip()) < 50:
            return file_type, text, "Nội dung trích xuất được khá ngắn. Kết quả hỏi đáp có thể chưa tốt."

        return file_type, text, "Xử lý file thành công."

    except Exception as e:
        return "Error", "", f"Lỗi khi xử lý file: {e}"