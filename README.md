# Khánh AI Notebook V51

Ứng dụng Streamlit dùng để upload file PDF, đọc nội dung theo từng mục và trả lời theo đúng cấu trúc trong tài liệu. App hỗ trợ hiển thị xen kẽ **văn bản → hình ảnh/code box → văn bản**, giúp đọc tài liệu giống như đang xem lại file gốc.

## 1. Chức năng chính

* Upload file PDF.
* Tách nội dung PDF thành từng mục/section.
* Hỏi theo tên mục, ví dụ: `III.2. Chunking`, `4. Giả mã`, `IV.2. Tạo file ứng dụng`.
* Trả kết quả đúng phần được hỏi, không đọc lan sang mục khác.
* Giữ thứ tự nội dung trong file: văn bản, hình ảnh, code box, khung ghi chú.
* Hỗ trợ tìm mục có số La Mã như `III.2`, `IV.1` và mục số thường như `1.`, `2.`, `4.`.
* Nếu gõ hơi lệch tiêu đề, ví dụ `4. Giá mã` thay vì `4. Giả mã`, app vẫn ưu tiên tìm theo số mục `4.`.

## 2. Cấu trúc file

```text
project/
│
├── app.py
├── requirements.txt
├── INSTALL_V51.ps1
├── README.md
│
└── src/
    ├── __init__.py
    ├── config.py
    ├── pdf_section_interleaved.py
    └── rendering.py
```

## 3. Vai trò từng file

### `app.py`

File chính để chạy giao diện Streamlit.

Nhiệm vụ:

* Tạo giao diện upload PDF.
* Quản lý danh sách file đã upload.
* Nhận câu hỏi từ người dùng.
* Gọi hàm đọc PDF trong `pdf_section_interleaved.py`.
* Hiển thị kết quả trả lời ra màn hình.
* Hiển thị sidebar gồm nguồn tài liệu, version và debug.

Chạy app bằng lệnh:

```powershell
python -m streamlit run app.py
```

---

### `requirements.txt`

Chứa danh sách thư viện cần cài.

Các thư viện chính:

```text
streamlit
pymupdf
pillow
```

Trong đó:

* `streamlit`: tạo giao diện web.
* `pymupdf`: đọc PDF, tách text, crop hình ảnh/code box.
* `pillow`: hỗ trợ xử lý hình ảnh.

Cài bằng lệnh:

```powershell
pip install -r requirements.txt
```

---

### `INSTALL_V51.ps1`

File cài đặt nhanh cho Windows PowerShell.

Nhiệm vụ:

* Tắt tiến trình Python/Streamlit cũ.
* Xóa thư mục `src` và `runtime` cũ trong `D:\aio`.
* Copy code mới vào `D:\aio`.
* Cài thư viện từ `requirements.txt`.
* Kiểm tra version app.

Chạy bằng lệnh:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\INSTALL_V51.ps1
```

---

### `src/config.py`

File cấu hình chung của app.

Nội dung chính:

```python
APP_VERSION = "NUMERIC_SECTION_FUZZY_FIX_V51"
PDF_ZOOM = 2.0
RUNTIME_DIR = "runtime"
SHOW_COPY_TEXT = False
```

Ý nghĩa:

* `APP_VERSION`: tên phiên bản hiện tại.
* `PDF_ZOOM`: độ nét khi crop ảnh/code box từ PDF.
* `RUNTIME_DIR`: thư mục lưu file upload và ảnh tạm.
* `SHOW_COPY_TEXT`: bật/tắt phần text copy. Mặc định tắt để giao diện gọn hơn.

---

### `src/pdf_section_interleaved.py`

File xử lý PDF quan trọng nhất.

Nhiệm vụ chính:

* Đọc text trong PDF.
* Nhận diện heading/mục như `III.2. Chunking`, `4. Giả mã`, `IV.2. Tạo file ứng dụng`.
* Xác định điểm bắt đầu và kết thúc của mục được hỏi.
* Tránh đọc dư sang mục tiếp theo.
* Nhận diện hình ảnh, caption, code box và khung ghi chú.
* Crop hình ảnh/code box từ PDF.
* Trả kết quả theo thứ tự xen kẽ:

```text
văn bản → hình/code/box → văn bản → hình/code/box
```

Các nhóm hàm chính:

* Hàm chuẩn hóa text: xử lý dấu, khoảng trắng, lỗi tách chữ.
* Hàm nhận diện mục: tìm heading trong PDF.
* Hàm cắt section: lấy đúng nội dung của mục được hỏi.
* Hàm nhận diện ảnh/code/box: quyết định phần nào hiển thị dạng text, phần nào crop thành ảnh.
* Hàm `build_interleaved_blocks()`: hàm chính dùng để tạo kết quả trả lời.

---

### `src/rendering.py`

File hiển thị kết quả ra giao diện Streamlit.

Nhiệm vụ:

* Hiển thị block văn bản.
* Hiển thị block hình ảnh.
* Hiển thị caption nếu có.
* Render toàn bộ kết quả theo đúng thứ tự đã xử lý từ PDF.

Các hàm chính:

* `render_text_block()`: hiển thị văn bản.
* `render_image_block()`: hiển thị ảnh/code box.
* `render_interleaved_result()`: hiển thị toàn bộ kết quả gồm cả text và ảnh.

---

### `src/__init__.py`

File đánh dấu thư mục `src` là một Python package.

File này thường để trống nhưng cần có để Python import các module trong `src`.

---

### `runtime/`

Thư mục được tạo tự động khi chạy app.

Nhiệm vụ:

* Lưu file PDF người dùng upload.
* Lưu ảnh/code box đã crop từ PDF.
* Lưu dữ liệu tạm trong quá trình chạy.

Có thể xóa thư mục này khi muốn reset app hoặc upload file mới.

---

## 4. Cách sử dụng

### Bước 1: Cài thư viện

```powershell
pip install -r requirements.txt
```

### Bước 2: Chạy app

```powershell
python -m streamlit run app.py
```

### Bước 3: Upload PDF

Ở sidebar bên trái:

1. Chọn file PDF.
2. Bấm `Tạo notebook`.
3. Đợi app xử lý xong.

### Bước 4: Hỏi nội dung trong file

Ví dụ:

```text
III.2. Chunking
```

```text
III.3. Embedding và lưu vào Vector Database
```

```text
4. Giả mã
```

```text
hình 2
```

```text
Mục lục
```

## 5. Lưu ý khi đổi file PDF

Khi đổi sang file PDF khác, nên làm theo thứ tự:

1. Bấm `Xóa` trong app.
2. Upload file PDF mới.
3. Bấm `Tạo notebook`.
4. Hỏi lại theo mục trong file mới.

Nếu không xóa notebook cũ, app có thể còn dùng dữ liệu tạm của file trước.

## 6. Phiên bản V51 đã sửa gì?

Bản V51 sửa các lỗi chính:

* Hỏi mục số thường như `4. Giả mã` không còn bị lỗi.
* Gõ lệch nhẹ như `4. Giá mã` vẫn tìm được vì app ưu tiên số mục.
* Các dòng giả mã như `1. Đặt left...`, `2. Trong khi...` không bị hiểu nhầm là section mới.
* Hỏi `III.2. Chunking` không còn bị đọc dư sang phần `IV`.
* Hỏi các mục La Mã như `IV.2. Tạo file ứng dụng` vẫn hoạt động.
* Code box được crop thành ảnh nguyên khối thay vì bị tách vụn.

## 7. Giới hạn hiện tại

* App phụ thuộc vào cách PDF được xuất text. Nếu PDF scan ảnh hoàn toàn, cần OCR mới đọc tốt.
* Một số PDF có layout quá phức tạp có thể cần chỉnh thêm logic nhận diện heading.
* App hiện tập trung vào đọc PDF theo mục, chưa phải chatbot suy luận sâu như LLM.
* Nếu muốn hỏi ý nghĩa, tóm tắt hoặc giải thích nâng cao, có thể cần tích hợp thêm model LLM.
