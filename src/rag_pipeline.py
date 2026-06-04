import ollama


def generate_answer(question, retrieved_chunks):
    """
    Sinh câu trả lời dựa trên các chunk tìm được từ PDF.
    """
    context = "\n\n".join(retrieved_chunks)

    prompt = f"""
Bạn là chatbot trả lời dựa trên tài liệu PDF được cung cấp.

Chỉ sử dụng thông tin trong phần CONTEXT để trả lời.
Nếu không tìm thấy thông tin trong tài liệu, hãy trả lời:
"Tôi không tìm thấy thông tin này trong tài liệu."

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""

    response = ollama.chat(
        model="llama3.2",
        messages=[
            {"role": "user", "content": prompt}
        ],
        options={
            "temperature": 0.2
        }
    )

    return response["message"]["content"]