# =========================
# MODEL CONFIG
# =========================

LLM_MODEL = "llama3.2"
EMBED_MODEL = "nomic-embed-text"
VISION_MODEL = "llama3.2-vision"

# Có thể thử sau:
# LLM_MODEL = "qwen2.5:3b"
# LLM_MODEL = "gemma2:9b"
# EMBED_MODEL = "bge-m3"


# =========================
# RAG CONFIG
# =========================

CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200
N_RESULTS = 4
TEMPERATURE = 0
#"CHUNK_SIZE = 800( chạy thử hết tất cả  )
#CHUNK_SIZE = 1000
#CHUNK_SIZE = 1500"
#N_RESULTS = 3
#N_RESULTS = 4
#N_RESULTS = 5
#TEMPERATURE = 0
#TEMPERATURE = 0.2
# =========================
# MULTIMODAL CONFIG
# =========================

MAX_PDF_VISION_PAGES = 6
MAX_VIDEO_FRAMES = 6
MAX_FILE_SIZE_MB = 200
