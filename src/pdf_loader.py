from pypdf import PdfReader


def read_pdf(file_path):
    """
    Đọc nội dung text từ file PDF.
    """
    reader = PdfReader(file_path)
    text = ""

    for page in reader.pages:
        page_text = page.extract_text()
        if page_text:
            text += page_text + "\n"

    return text