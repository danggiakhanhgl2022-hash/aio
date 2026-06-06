# Khánh AI Notebook V50

Bản V50 sửa lỗi không tìm thấy các mục IV / IV.1 / IV.2.

Lỗi trước:
- Hỏi `IV.2. Tạo file ứng dụng` hoặc `IV. Xây dựng giao diện với Streamlit` thì báo không tìm thấy.
- Nguyên nhân: app nhận nhầm trang 11 là trang Mục lục vì trang đó có nhiều heading IV, IV.1, IV.2 và có dấu `...` trong code.

Fix V50:
- Chỉ coi là Mục lục nếu có chữ `Mục lục` ở đầu trang hoặc nhiều dòng dot-leader dạng `........ 7`.
- Các mục IV, IV.1, IV.2 sẽ được tìm đúng.
- Vẫn giữ strict stop: hỏi III.2 sẽ không ăn sang IV.

Cách chạy:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\INSTALL_V50.ps1
```

Trong app phải thấy version: `TOC_FALSE_POSITIVE_FIX_V50`.

Sau đó bấm Xóa, upload lại PDF và hỏi:
- `IV.2. Tạo file ứng dụng`
- `IV. Xây dựng giao diện với Streamlit`
- `III.2. Chunking`
