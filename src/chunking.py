def chunk_text(text, chunk_size=800, overlap=150):
    """
    Chia văn bản dài thành các đoạn nhỏ.

    chunk_size: số ký tự trong mỗi chunk.
    overlap: số ký tự lặp lại giữa 2 chunk liên tiếp.
    """
    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start += chunk_size - overlap

    return chunks