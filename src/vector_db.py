import chromadb
import ollama


def get_embedding(text):
    """
    Tạo embedding cho một đoạn text bằng Ollama.
    Embedding là dạng vector số để máy tính hiểu ý nghĩa của văn bản.
    """
    response = ollama.embeddings(
        model="nomic-embed-text",
        prompt=text
    )
    return response["embedding"]


def create_vector_db(chunks):
    """
    Tạo vector database từ các chunks.
    Mỗi chunk sẽ được chuyển thành embedding rồi lưu vào ChromaDB.
    """
    client = chromadb.Client()

    collection = client.get_or_create_collection(
        name="pdf_collection"
    )

    for i, chunk in enumerate(chunks):
        embedding = get_embedding(chunk)

        collection.add(
            ids=[str(i)],
            embeddings=[embedding],
            documents=[chunk]
        )

    return collection


def retrieve_chunks(collection, question, n_results=3):
    """
    Tìm các chunk liên quan nhất với câu hỏi.
    n_results=3 nghĩa là lấy 3 đoạn liên quan nhất.\
    .....
    """
    question_embedding = get_embedding(question)

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=n_results
    )

    return results["documents"][0]