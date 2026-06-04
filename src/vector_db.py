import re
import time
import chromadb
import ollama

from src.config import EMBED_MODEL


def get_embeddings(texts):
    """
    Chuyển danh sách text thành embedding vector.
    """
    if not texts:
        return []

    response = ollama.embed(
        model=EMBED_MODEL,
        input=texts
    )

    return response["embeddings"]


def create_vector_db(chunks):
    """
    Tạo ChromaDB collection từ danh sách chunks.
    Lưu metadata để biết chunk số mấy.
    """
    if not chunks:
        raise ValueError("Không có chunk nào để lưu vào vector database.")

    client = chromadb.Client()

    collection_name = f"rag_{int(time.time())}"

    collection = client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )

    embeddings = get_embeddings(chunks)

    collection.add(
        ids=[str(i) for i in range(len(chunks))],
        documents=chunks,
        embeddings=embeddings,
        metadatas=[{"chunk_id": i} for i in range(len(chunks))]
    )

    return collection


def extract_keywords(question):
    """
    Tách keyword quan trọng từ câu hỏi.
    Hỗ trợ tốt hơn cho câu hỏi về số điện thoại, email, ngày tháng, mã số, tên riêng.
    """
    question_lower = question.lower()

    keywords = []

    # Keyword thủ công hay gặp
    important_terms = [
        "sđt", "zalo", "sdt", "số điện thoại", "điện thoại",
        "email", "gmail", "ngày", "tháng", "năm",
        "tác giả", "người thực hiện", "biên soạn",
        "project", "module", "địa chỉ", "liên hệ"
    ]

    for term in important_terms:
        if term in question_lower:
            keywords.append(term)

    # Bắt các chuỗi số trong câu hỏi
    numbers = re.findall(r"\d+", question_lower)
    keywords.extend(numbers)

    # Tách thêm từ dài hơn 2 ký tự
    words = re.findall(r"[a-zA-ZÀ-ỹ0-9/]+", question_lower)
    for word in words:
        if len(word) >= 3:
            keywords.append(word)

    # Loại trùng
    unique_keywords = []
    seen = set()

    for kw in keywords:
        if kw not in seen:
            unique_keywords.append(kw)
            seen.add(kw)

    return unique_keywords


def keyword_search_chunks(collection, question, max_results=6):
    """
    Tìm chunk bằng keyword search.
    Dùng cho các câu hỏi về số điện thoại, Zalo, email, mã số, tên riêng.
    """
    try:
        all_data = collection.get(include=["documents"])
        documents = all_data.get("documents", [])
    except Exception:
        return []

    keywords = extract_keywords(question)

    matched_chunks = []

    for doc in documents:
        doc_lower = doc.lower()

        score = 0

        for kw in keywords:
            if kw.lower() in doc_lower:
                score += 1

        # Ưu tiên chunk có số nếu câu hỏi hỏi về số/SĐT/Zalo
        if any(term in question.lower() for term in ["sđt", "sdt", "zalo", "số điện thoại", "điện thoại"]):
            if re.search(r"\d{8,12}", doc):
                score += 3

        if score > 0:
            matched_chunks.append((score, doc))

    matched_chunks.sort(key=lambda x: x[0], reverse=True)

    return [doc for score, doc in matched_chunks[:max_results]]


def retrieve_chunks(collection, question, n_results=6):
    """
    Tìm các chunk liên quan nhất.

    Bản cải tiến:
    1. Semantic search bằng embedding.
    2. Keyword search cho số điện thoại, Zalo, email, mã số, tên riêng.
    3. Luôn thêm chunk đầu tài liệu vì thường chứa tiêu đề/tác giả.
    """

    if collection is None:
        return []

    # 1. Semantic search
    try:
        question_embedding = get_embeddings([question])[0]

        results = collection.query(
            query_embeddings=[question_embedding],
            n_results=n_results
        )

        semantic_docs = results.get("documents", [[]])[0]
    except Exception:
        semantic_docs = []

    # 2. Keyword search
    keyword_docs = keyword_search_chunks(
        collection=collection,
        question=question,
        max_results=n_results
    )

    # 3. Luôn lấy chunk đầu
    try:
        first_chunks = collection.get(
            ids=["0", "1"],
            include=["documents"]
        ).get("documents", [])
    except Exception:
        first_chunks = []

    # 4. Gộp lại, ưu tiên keyword trước
    final_chunks = []
    seen = set()

    for doc in keyword_docs + first_chunks + semantic_docs:
        if doc and doc not in seen:
            final_chunks.append(doc)
            seen.add(doc)

    return final_chunks