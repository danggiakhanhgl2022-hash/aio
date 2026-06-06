try:
    import ollama
except Exception:
    ollama = None

try:
    from src.config import LLM_MODEL
except Exception:
    LLM_MODEL = "llama3.2:latest"


def generate_answer(question_or_prompt, chunks):
    """
    Sinh câu trả lời bằng Ollama.
    Nếu Ollama lỗi, trả về câu trả lời fallback dựa trên nguồn.
    """
    sources = "\n\n".join(
        f"[Nguồn {i+1}]\n{chunk[:2500]}"
        for i, chunk in enumerate(chunks or [])
    )

    if not sources.strip():
        return "Tôi không tìm thấy thông tin này trong tài liệu đã tải lên."

    prompt = f"""
Bạn là trợ lý hỏi đáp tài liệu.

Chỉ được dùng phần NGUỒN bên dưới để trả lời.
Không bịa thêm ngoài nguồn.
Nếu nguồn có thông tin liên quan, hãy trả lời dựa trên nguồn.
Chỉ nói không tìm thấy khi nguồn thật sự không có thông tin liên quan.

CÂU HỎI:
{question_or_prompt}

NGUỒN:
{sources}

TRẢ LỜI BẰNG TIẾNG VIỆT:
"""

    if ollama is None:
        return fallback_answer(sources)

    try:
        response = ollama.chat(
            model=LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            options={"temperature": 0},
        )

        if isinstance(response, dict):
            content = response.get("message", {}).get("content", "")

            if content.strip():
                return content.strip()

        if hasattr(response, "message") and hasattr(response.message, "content"):
            content = response.message.content

            if content.strip():
                return content.strip()

    except Exception as e:
        return fallback_answer(sources, error=str(e))

    return fallback_answer(sources)


def fallback_answer(sources, error=None):
    msg = "Tôi tìm thấy các đoạn nguồn liên quan trong tài liệu, nhưng LLM/Ollama chưa trả lời được."

    if error:
        msg += f"\n\nLỗi LLM: {error}"

    msg += "\n\nĐoạn nguồn liên quan:\n" + sources[:1800]
    return msg