# Khánh AI Notebook - Final Robust V4

## Cách cài

Copy toàn bộ thư mục/file vào project `D:\aio`.

Quan trọng nhất là các file:

- app.py
- src/config.py
- src/chunking.py
- src/vector_db.py
- src/rag_pipeline.py
- src/multimodal_loader.py

## Cài thư viện

```powershell
pip install streamlit pypdf pymupdf ollama
```

## Chạy app

```powershell
python -m streamlit run app.py
```

## Kiểm tra đúng bản

Trên giao diện phải thấy:

FINAL_ROBUST_TEXT_IMAGE_V4

## Quy trình test

1. Bấm Xóa
2. Upload lại PDF
3. Bấm Tạo notebook
4. Hỏi:
   - Large Language Models
   - hinh 1
   - hinh 2

## Lưu ý

- Với PDF có chữ thật: đọc tốt văn bản và caption hình.
- Với PDF scan/mờ: cần model vision như llava hoặc OCR, kết quả không thể đảm bảo 100%.
- Với hình trong PDF có caption: hệ thống ưu tiên caption + text gần hình, không dùng vision để bịa.