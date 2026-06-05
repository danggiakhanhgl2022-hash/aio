import ollama

from src.config import LLM_MODEL, TEMPERATURE


PROMPT_TEMPLATE = """
Bạn là trợ lý hỏi đáp dữ liệu.

QUY TẮC BẮT BUỘC:
- Chỉ sử dụng thông tin trong CONTEXT để trả lời.
- Không được thêm kiến thức ngoài CONTEXT.
- Không được tự bổ sung bước, công nghệ, thuật toán nếu CONTEXT không nhắc đến.
- Nếu CONTEXT là nội dung trích xuất từ ảnh, hãy trả lời dựa đúng vào mô tả ảnh đó.
- Nếu câu hỏi hỏi về hình ảnh, sơ đồ, biểu đồ hoặc slide, hãy mô tả đúng các thành phần nhìn thấy trong CONTEXT.
- Nếu câu hỏi hỏi về Large Language Models, LLM, AI, machine learning, deep learning, hãy chỉ trả lời theo các thông tin có trong CONTEXT.
- Nếu câu hỏi hỏi về số điện thoại, SĐT, Zalo, email, mã số, ngày tháng, hãy tìm chính xác các con số hoặc ký hiệu trong CONTEXT.
- Nếu câu hỏi hỏi "ai", "của ai", "tác giả", "người thực hiện", "người biên soạn", hãy tìm tên người trong CONTEXT.
- Nếu CONTEXT thật sự không có thông tin liên quan, hãy nói đúng câu: "Tôi không tìm thấy thông tin này trong dữ liệu đã tải lên."
- Không tự bịa thêm thông tin.
- Trả lời bằng tiếng Việt.
- Trả lời ngắn gọn, rõ ràng.

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