import ollama

from src.config import LLM_MODEL, TEMPERATURE


PROMPT_TEMPLATE = """
Bạn là trợ lý hỏi đáp dữ liệu.

Nhiệm vụ:
- Chỉ sử dụng thông tin trong CONTEXT để trả lời.
- Nếu câu hỏi hỏi về số điện thoại, SĐT, Zalo, email, mã số, ngày tháng, hãy tìm chính xác các con số hoặc ký hiệu trong CONTEXT.
- Nếu câu hỏi hỏi "ai", "của ai", "tác giả", "người thực hiện", "người biên soạn", hãy tìm tên người trong CONTEXT.
- Nếu CONTEXT có thông tin liên hệ như SĐT/Zalo, hãy trả lời đúng nguyên văn số liên hệ.
- Nếu CONTEXT thật sự không có thông tin, hãy nói: "Tôi không tìm thấy thông tin này trong dữ liệu đã tải lên."
- Không tự bịa thêm thông tin.
- Trả lời bằng tiếng Việt.
- Trả lời rõ ràng, ngắn gọn, dễ hiểu.

CONTEXT:
{context}

QUESTION:
{question}

ANSWER:
"""


def generate_answer(question, retrieved_chunks):
    """
    Sinh câu trả lời dựa trên context đã retrieve.
    Đây là phần LLM trong pipeline RAG.
    """

    if not retrieved_chunks:
        return "Tôi không tìm thấy thông tin liên quan trong dữ liệu đã tải lên."

    context = "\n\n".join(retrieved_chunks)

    prompt = PROMPT_TEMPLATE.format(
        context=context,
        question=question
    )

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[
                {"role": "user", "content": prompt}
            ],
            options={
                "temperature": TEMPERATURE
            }
        )

        return response["message"]["content"]

    except Exception as e:
        return f"Lỗi khi gọi mô hình LLM: {e}"
    #LLM_MODEL = "llama3.2"
    #LLM_MODEL = "llama3.2"
    #LLM_MODEL = "qwen2.5:3b"
    #LLM_MODEL = "gemma2:9b"
    #TEMPERATURE = 0.2
    #TEMPERATURE = 0
    