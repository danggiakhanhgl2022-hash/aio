# Khánh AI Notebook V51

Bản V51 sửa lỗi khi đổi sang PDF khác có mục số thường như `4. Giả mã`.

Lỗi trước:
- Gõ `4. Giá mã` / `4. Giả mã` có thể báo không tìm thấy.
- Nguyên nhân 1: app bắt tiêu đề quá chính xác, trong khi người dùng có thể gõ sai dấu/sai chữ.
- Nguyên nhân 2: trong mục `4. Giả mã`, các dòng giả mã `1. Đặt left...`, `2. Trong khi...`
  bị hiểu nhầm là heading mới nên section bị cắt sai.

Fix V51:
- Nếu số mục khớp, ví dụ `4.` thì app tìm đúng mục 4 dù tiêu đề gõ lệch nhẹ.
- Dòng giả mã/danh sách số bên trong mục không còn bị hiểu là section mới.
- Chỉ dừng khi gặp mục kế tiếp thật, ví dụ `5. Cài đặt Python`.
- Placeholder đã đổi sang dạng chung, phù hợp khi đổi PDF.

Cách chạy:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\INSTALL_V51.ps1
```

Trong app phải thấy version: `NUMERIC_SECTION_FUZZY_FIX_V51`.

Sau đó bấm Xóa, upload lại PDF mới và hỏi:
- `4. Giả mã`
- `4. Giá mã`
- `2. Điều kiện áp dụng`
