# Khánh AI Notebook V52

Bản V52 giữ nguyên chức năng của V51 nhưng đã tách phần xử lý PDF thành nhiều file nhỏ để dễ đọc, dễ sửa và dễ debug hơn.

## 1. Chức năng chính

App dùng Streamlit để upload PDF và hỏi theo mục trong tài liệu.

Kết quả được hiển thị theo đúng thứ tự trong file:

```text
văn bản → hình ảnh/code box/khung ghi chú → văn bản → hình ảnh
```

Ví dụ câu hỏi:

```text
III.2. Chunking
4. Giả mã
IV.2. Tạo file ứng dụng
hình 2
Mục lục
```

## 2. Cấu trúc project

```text
project/
│
├── app.py
├── requirements.txt
├── INSTALL_V52.ps1
├── README.md
│
└── src/
    ├── __init__.py
    ├── config.py
    ├── rendering.py
    │
    ├── pdf_section_interleaved.py
    ├── pdf_utils.py
    ├── pdf_sections.py
    ├── pdf_blocks.py
    └── pdf_interleaved.py
```

## 3. Vai trò từng file

### `app.py`

File giao diện chính của Streamlit.

Nhiệm vụ:

- Upload PDF.
- Tạo notebook.
- Nhận câu hỏi từ người dùng.
- Gọi hàm xử lý PDF.
- Hiển thị kết quả.
- Hiển thị sidebar, nguồn tài liệu và debug.

Chạy app:

```powershell
python -m streamlit run app.py
```

---

### `src/config.py`

File cấu hình chung.

Nội dung chính:

```python
APP_VERSION = "REFACTORED_PDF_MODULES_V52"
PDF_ZOOM = 2.0
RUNTIME_DIR = "runtime"
SHOW_COPY_TEXT = False
```

Ý nghĩa:

- `APP_VERSION`: tên phiên bản hiện tại.
- `PDF_ZOOM`: độ nét khi crop ảnh/code box.
- `RUNTIME_DIR`: thư mục lưu dữ liệu tạm.
- `SHOW_COPY_TEXT`: bật/tắt phần text copy.

---

### `src/rendering.py`

File hiển thị kết quả lên giao diện.

Nhiệm vụ:

- Hiển thị văn bản.
- Hiển thị hình ảnh/code box.
- Hiển thị caption nếu có.
- Render kết quả xen kẽ theo đúng thứ tự đã xử lý.

Hàm chính:

```python
render_text_block()
render_image_block()
render_interleaved_result()
```

---

### `src/pdf_section_interleaved.py`

File trung gian để giữ tương thích với `app.py`.

Trước đây toàn bộ code PDF nằm trong file này. Từ V52, file này chỉ import lại các hàm chính từ các file nhỏ hơn.

Nhờ vậy `app.py` vẫn dùng được import cũ:

```python
from src.pdf_section_interleaved import build_interleaved_blocks
```

---

### `src/pdf_utils.py`

File chứa hàm tiện ích dùng chung khi xử lý PDF.

Nhiệm vụ:

- Chuẩn hóa text.
- Bỏ dấu tiếng Việt để so sánh dễ hơn.
- Sửa một số lỗi text bị dính chữ sau khi extract PDF.
- Lấy text từ block PDF.
- Lấy tọa độ block.
- Crop vùng ảnh/code box từ PDF.
- Nhận diện header/footer.
- Nhận diện trang mục lục.

Hàm quan trọng:

```python
norm()
clean_text_display()
extract_block_text()
block_rect()
union_rect()
crop_region()
crop_union()
is_footer_or_header()
is_toc_page()
```

---

### `src/pdf_sections.py`

File xử lý việc tìm mục/section trong PDF.

Nhiệm vụ:

- Nhận diện heading như `III.2. Chunking`, `4. Giả mã`, `IV.2. Tạo file ứng dụng`.
- Tách mã mục và tên mục.
- So sánh số mục La Mã và số thường.
- Tìm điểm bắt đầu và kết thúc của section.
- Tránh đọc dư sang mục kế tiếp.
- Hỗ trợ tìm gần đúng khi tiêu đề gõ hơi lệch.

Hàm quan trọng:

```python
parse_section_id_from_text()
looks_like_heading()
split_query_section()
fuzzy_title_match()
should_end_section()
should_stop_at_heading()
find_section_range()
```

---

### `src/pdf_blocks.py`

File phân loại các block nằm trong section.

Nhiệm vụ:

- Nhận diện caption hình ảnh.
- Nhận diện bullet.
- Nhận diện dòng code.
- Nhận diện tiêu đề code box.
- Nhận diện box/khung ghi chú.
- Lấy toàn bộ block thô trong section.
- Thêm text block vào output.

Hàm quan trọng:

```python
is_caption_text()
is_bullet_paragraph()
is_numbered_line()
is_code_line()
is_code_panel_title()
is_box_title()
collect_raw_blocks()
add_text_block()
```

---

### `src/pdf_interleaved.py`

File điều phối chính để tạo câu trả lời.

Nhiệm vụ:

- Gọi `find_section_range()` để tìm mục cần đọc.
- Gọi `collect_raw_blocks()` để lấy nội dung trong mục.
- Duyệt từng block theo đúng thứ tự trong PDF.
- Block văn bản thì giữ dạng text.
- Block hình/code box/khung ghi chú thì crop thành ảnh.
- Trả kết quả theo dạng xen kẽ.

Hàm quan trọng:

```python
build_interleaved_blocks()
extract_toc_as_text()
find_figure_by_number()
```

Trong đó `build_interleaved_blocks()` là hàm quan trọng nhất.

---

### `requirements.txt`

Danh sách thư viện cần cài:

```text
streamlit
pymupdf
pillow
```

Cài thư viện:

```powershell
pip install -r requirements.txt
```

---

### `INSTALL_V52.ps1`

File cài nhanh trên Windows.

Nhiệm vụ:

- Tắt Python/Streamlit cũ.
- Xóa `src`, `runtime`, `__pycache__` cũ trong `D:\aio`.
- Copy code mới vào `D:\aio`.
- Cài thư viện.
- In version để kiểm tra.

Chạy:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\INSTALL_V52.ps1
```

---

### `runtime/`

Thư mục được tạo tự động khi chạy app.

Nhiệm vụ:

- Lưu PDF đã upload.
- Lưu ảnh/code box đã crop.
- Lưu dữ liệu tạm.

Có thể xóa thư mục này khi muốn reset app hoặc upload PDF mới.

## 4. Luồng xử lý chính

Khi người dùng hỏi một mục, app chạy theo luồng:

```text
app.py
→ pdf_section_interleaved.py
→ pdf_interleaved.py
→ pdf_sections.py tìm section
→ pdf_blocks.py phân loại block
→ pdf_utils.py crop ảnh/làm sạch text
→ rendering.py hiển thị kết quả
```

## 5. Cách chạy

Cài thư viện:

```powershell
pip install -r requirements.txt
```

Chạy app:

```powershell
python -m streamlit run app.py
```

Hoặc cài nhanh:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\INSTALL_V52.ps1
```

## 6. Khi đổi PDF

Khi đổi sang file PDF khác:

1. Bấm `Xóa`.
2. Upload PDF mới.
3. Bấm `Tạo notebook`.
4. Hỏi lại theo mục trong file mới.

Nếu không xóa, app có thể còn dữ liệu tạm của file trước.

## 7. Gợi ý sửa code

Sửa logic nhận diện heading:

```text
src/pdf_sections.py
```

Sửa logic nhận diện code box/hình/box:

```text
src/pdf_blocks.py
```

Sửa logic crop ảnh hoặc làm sạch text:

```text
src/pdf_utils.py
```

Sửa luồng tạo kết quả xen kẽ text + ảnh:

```text
src/pdf_interleaved.py
```

Sửa giao diện:

```text
app.py
src/rendering.py
```


---

## V53 - Sửa lỗi `ValueError: document closed`

Lỗi nằm trong `src/pdf_sections.py`.

Sai:

```python
doc.close()
return {**found, "end_page": len(doc) - 1, "end_y": None}
```

Đúng:

```python
last_page = len(doc) - 1
doc.close()
return {**found, "end_page": last_page, "end_y": None}
```

Lý do: sau khi `doc.close()`, PyMuPDF không cho gọi `len(doc)` nữa.


---

## V54 - Bản sửa cuối lỗi `ValueError: document closed`

Phiên bản: `FINAL_DOCUMENT_CLOSED_FIX_V54`

Lỗi cũ:
```python
doc.close()
return {**found, "end_page": len(doc) - 1, "end_y": None}
```

Nguyên nhân: sau khi `doc.close()`, PyMuPDF không cho gọi `len(doc)` nữa.

Cách sửa trong `src/pdf_sections.py`:
```python
doc = fitz.open(pdf_path)
page_count = len(doc)
...
for page_index in range(page_count):
    ...
for page_index in range(found["start_page"], page_count):
    ...
doc.close()
return {**found, "end_page": page_count - 1, "end_y": None}
```

Bản này cũng giữ regex số La Mã mở rộng trong `src/pdf_utils.py`, hỗ trợ các mục như `XXI`, `XXX`, `XL`.


---

## V55 - Sửa triệt để `ValueError: document closed`

File sửa: `src/pdf_sections.py`

Hàm `find_section_range()` đã được viết lại an toàn:

```python
doc = fitz.open(pdf_path)
page_count = len(doc)

try:
    ...
finally:
    doc.close()
```

Điểm quan trọng:
- Không gọi `len(doc)` sau khi `doc.close()`.
- Không đóng PDF giữa hàm rồi tiếp tục dùng PDF.
- Nếu section nằm cuối file, app dùng `page_count - 1`, không dùng `len(doc)` nữa.

Version trong app:

```text
NO_DOCUMENT_CLOSE_BUG_V55
```


---

## V56 - Sửa dính chữ và ẩn Clear caches

Phiên bản: `TEXT_SPACING_NO_CACHE_MODAL_V56`

### 1. Sửa lỗi dính chữ khi extract PDF

File sửa:

```text
src/pdf_utils.py
```

Thêm hàm:

```python
fix_vietnamese_spacing()
```

Hàm này xử lý các lỗi như:

```text
kỹthuật -> kỹ thuật
đểLLM -> để LLM
trảlời -> trả lời
cụthể -> cụ thể
cửa sổngữcảnh -> cửa sổ ngữ cảnh
```

### 2. Ẩn menu Clear caches của Streamlit

File sửa:

```text
app.py
```

Thêm CSS ẩn menu/toolbar mặc định của Streamlit để tránh bấm nhầm `Clear caches` khi thao tác copy.

Nếu vẫn hiện popup `Clear caches`, chỉ cần bấm `Cancel` hoặc dấu `X`. Đây là popup của Streamlit, không phải lỗi xử lý PDF.


---

## V57 - Mở rộng sửa lỗi dính chữ tiếng Việt

Phiên bản: `VIETNAMESE_SPACING_FIX_V57`

File sửa chính:

```text
src/pdf_utils.py
```

Hàm `fix_vietnamese_spacing()` được mở rộng để xử lý thêm:

```text
vềmột -> về một
chủđềphức tạp -> chủ đề phức tạp
cụ thểmà -> cụ thể mà
toàn bộtài liệu -> toàn bộ tài liệu
sẽgiải -> sẽ giải
khảnăng -> khả năng
thểtrả -> thể trả
vềtài liệu -> về tài liệu
luồng xửlý -> luồng xử lý
```

Ngoài ra thêm:

```text
.streamlit/config.toml
```

để giảm hiện menu/toolbar Streamlit.


---

## V58 - Sửa dính chữ theo cách tổng quát hơn

Phiên bản: `GENERAL_PDF_SPACING_FIX_V58`

File sửa chính:

```text
src/pdf_utils.py
```

Bản V58 sửa ở gốc hơn: thay vì chỉ sửa từng cụm từ bị dính, app đổi cách đọc text từ PDF.

Trước đây:

```python
line_text += span["text"]
```

Cách này dễ làm chữ bị dính nếu PDF tách một dòng thành nhiều span.

Bây giờ:

```python
line_text = _line_text_from_spans(line)
```

Hàm mới xét tọa độ `x0/x1` giữa 2 span. Nếu trên trang PDF có khoảng cách vật lý giữa 2 cụm chữ, app tự thêm khoảng trắng.

Cách này áp dụng tốt hơn cho file PDF bất kỳ, miễn là PDF có text thật.

Giới hạn:
- Nếu PDF là ảnh scan hoàn toàn, cần OCR riêng.
- Nếu chữ đã bị dính ngay trong cùng một span của PDF, app vẫn dùng thêm `fix_vietnamese_spacing()` để sửa hậu xử lý.
