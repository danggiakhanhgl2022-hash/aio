import math
import re
import unicodedata

try:
    import ollama
except Exception:
    ollama = None

try:
    from src.config import EMBED_MODEL
except Exception:
    EMBED_MODEL = "nomic-embed-text:latest"


def normalize_text(text: str) -> str:
    if not text:
        return ""

    text = str(text)
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = text.replace("đ", "d").replace("Đ", "D")
    return text.lower().strip()


def tokenize(text: str):
    text = normalize_text(text)
    tokens = re.split(r"[^a-zA-Z0-9À-Ỵà-ỵ]+", text)
    stop = {
        "la", "là", "gi", "gì", "cua", "của", "va", "và", "cho", "toi", "tôi",
        "hay", "hãy", "neu", "nêu", "ve", "về", "trong", "file", "tai", "tài",
        "lieu", "liệu", "mot", "một", "cac", "các", "nhung", "những"
    }
    return [t for t in tokens if len(t) >= 2 and t not in stop]


def cosine(a, b):
    if not a or not b or len(a) != len(b):
        return 0.0

    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))

    if na == 0 or nb == 0:
        return 0.0

    return dot / (na * nb)


def embed_text(text: str):
    if ollama is None:
        return None

    models = [EMBED_MODEL, "nomic-embed-text:latest", "bge-m3"]

    for model in models:
        try:
            response = ollama.embeddings(model=model, prompt=text[:4000])

            if isinstance(response, dict):
                emb = response.get("embedding")

                if emb:
                    return emb

            if hasattr(response, "embedding"):
                return response.embedding

        except Exception:
            continue

    return None


def keyword_score(question: str, chunk: str):
    q_norm = normalize_text(question)
    c_norm = normalize_text(chunk)
    tokens = tokenize(question)

    score = 0.0

    if q_norm and q_norm in c_norm:
        score += 50

    # phrase đặc biệt
    phrase_map = {
        "large language models": ["large language models", "llms", "llm", "mo hinh ngon ngu lon"],
        "retrieval augmented generation": ["retrieval augmented generation", "rag"],
        "vector database": ["vector database"],
    }

    for phrase, variants in phrase_map.items():
        if phrase in q_norm:
            for v in variants:
                if normalize_text(v) in c_norm:
                    score += 40

    for token in tokens:
        if token in c_norm:
            score += 5

    if "loai: pdf_text" in c_norm:
        score += 2

    if "loai: pdf_figure_context" in c_norm:
        score += 3

    return score


def create_vector_db(chunks):
    """
    Tạo collection dạng dict.
    Có embedding nếu Ollama embedding chạy được, nếu không fallback keyword search.
    """
    clean_chunks = [str(c) for c in chunks if str(c).strip()]
    embeddings = []
    embedding_ok = True

    for chunk in clean_chunks:
        emb = embed_text(chunk[:3000])

        if emb is None:
            embedding_ok = False
            embeddings = []
            break

        embeddings.append(emb)

    return {
        "chunks": clean_chunks,
        "embeddings": embeddings,
        "embedding_ok": embedding_ok,
    }


def retrieve_chunks(collection, question, n_results=6):
    if not collection:
        return []

    chunks = collection.get("chunks", [])
    embeddings = collection.get("embeddings", [])
    embedding_ok = collection.get("embedding_ok", False)

    q_emb = embed_text(question) if embedding_ok else None

    scored = []

    for idx, chunk in enumerate(chunks):
        k_score = keyword_score(question, chunk)
        e_score = 0.0

        if q_emb is not None and idx < len(embeddings):
            e_score = cosine(q_emb, embeddings[idx]) * 20

        score = k_score + e_score

        if score > 0:
            scored.append((score, -idx, chunk))

    # Nếu không có điểm, fallback lấy chunk đầu để tránh rỗng.
    if not scored:
        return chunks[:n_results]

    scored.sort(reverse=True)

    result = []
    seen = set()

    for _, _, chunk in scored:
        key = chunk[:350]

        if key not in seen:
            result.append(chunk)
            seen.add(key)

        if len(result) >= n_results:
            break

    return result