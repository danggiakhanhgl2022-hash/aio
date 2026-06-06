# Cấu hình model Ollama
LLM_MODEL = "llama3.2:latest"
EMBED_MODEL = "nomic-embed-text:latest"

# Nếu máy bạn đang dùng model khác, đổi tại đây:
# LLM_MODEL = "llama3.2:latest"
# EMBED_MODEL = "bge-m3"

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
N_RESULTS = 6