def chunk_text(text, chunk_size=1000, overlap=200):
    """
    Chia văn bản dài thành các chunk nhỏ có overlap.
    """
    text = str(text or "")

    if not text.strip():
        return []

    if chunk_size <= overlap:
        overlap = max(0, chunk_size // 5)

    chunks = []
    start = 0

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]

        if chunk.strip():
            chunks.append(chunk.strip())

        start += chunk_size - overlap

    return chunks