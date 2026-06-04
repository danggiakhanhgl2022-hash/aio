from src.config import CHUNK_SIZE, CHUNK_OVERLAP


def chunk_text(text, chunk_size=CHUNK_SIZE, overlap=CHUNK_OVERLAP):
    """
    Chia text thành các chunk nhỏ.
    overlap giúp giữ ngữ cảnh giữa 2 chunk liên tiếp.
    """

    if not text or not text.strip():
        return []

    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]

    chunks = []
    current = ""

    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 1 <= chunk_size:
            current += paragraph + "\n"
        else:
            if current.strip():
                chunks.append(current.strip())

            if overlap and len(current) > overlap:
                current = current[-overlap:] + "\n" + paragraph + "\n"
            else:
                current = paragraph + "\n"

    if current.strip():
        chunks.append(current.strip())

    # Fallback nếu text không có xuống dòng và quá dài
    if len(chunks) == 1 and len(chunks[0]) > chunk_size:
        raw_text = chunks[0]
        chunks = []
        start = 0

        while start < len(raw_text):
            end = start + chunk_size
            chunk = raw_text[start:end]

            if chunk.strip():
                chunks.append(chunk.strip())

            start += chunk_size - overlap

    return chunks
#CHUNK_SIZE = 800 ( chạy thử )
#CHUNK_OVERLAP = 160
#CHUNK_SIZE = 1000
#CHUNK_OVERLAP = 200
#CHUNK_SIZE = 1500
#CHUNK_OVERLAP = 300