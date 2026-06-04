import re


def direct_answer_from_text(question, extracted_text):
    """
    Trả lời trực tiếp các câu hỏi về thông tin chính xác:
    SĐT, Zalo, email, ngày tháng, mã số.
    Không cần qua retrieval.
    """

    if not question or not extracted_text:
        return None

    q = question.lower()
    text = extracted_text

    # =========================
    # SĐT / Zalo / điện thoại
    # =========================
    phone_keywords = [
        "sđt", "sdt", "zalo", "số điện thoại", "điện thoại",
        "phone", "hotline", "liên hệ"
    ]

    if any(keyword in q for keyword in phone_keywords):
        # Tìm dòng có SĐT/Zalo trước
        lines = text.split("\n")

        matched_lines = []
        for line in lines:
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in phone_keywords):
                matched_lines.append(line.strip())

        if matched_lines:
            return "Thông tin liên hệ trong dữ liệu là: " + " | ".join(matched_lines[:3])

        # Nếu không tìm thấy dòng, tìm số điện thoại 8-12 chữ số
        phone_numbers = re.findall(r"\b0\d{8,11}\b", text)

        if phone_numbers:
            unique_numbers = []
            for number in phone_numbers:
                if number not in unique_numbers:
                    unique_numbers.append(number)

            return "Số điện thoại/Zalo tìm thấy trong dữ liệu là: " + ", ".join(unique_numbers)

        return "Tôi không tìm thấy thông tin SĐT/Zalo trong dữ liệu đã tải lên."

    # =========================
    # Email
    # =========================
    email_keywords = ["email", "gmail", "mail"]

    if any(keyword in q for keyword in email_keywords):
        emails = re.findall(
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
            text
        )

        if emails:
            unique_emails = []
            for email in emails:
                if email not in unique_emails:
                    unique_emails.append(email)

            return "Email tìm thấy trong dữ liệu là: " + ", ".join(unique_emails)

        return "Tôi không tìm thấy email trong dữ liệu đã tải lên."

    return None