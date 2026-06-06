APP_VERSION = "SHOW_IMAGE_IN_CHAT_V32"

# Model sinh câu trả lời text
LLM_MODEL = "llama3.2:latest"

# Model đọc hình. Khuyên dùng llava:latest vì Ollama hỗ trợ vision ổn.
VISION_MODEL = "llava:latest"

# Kích thước chunk text
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120

# Số đoạn lấy cho câu hỏi text tự do
TOP_K = 5

# Render ảnh PDF. 2.0 đủ rõ mà không quá chậm.
PDF_RENDER_SCALE = 1.5

# Crop hình: lấy vùng phía trên caption.
FIGURE_CROP_HEIGHT = 340
