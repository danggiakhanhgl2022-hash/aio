"""
Facade giữ tương thích với app.py.

Từ V52, logic PDF đã được tách nhỏ:
- pdf_utils.py: tiện ích text/PDF/crop.
- pdf_sections.py: nhận diện và tìm section.
- pdf_blocks.py: phân loại block text/image/code/box.
- pdf_interleaved.py: build kết quả xen kẽ text + ảnh.
"""

from .pdf_utils import norm
from .pdf_interleaved import (
    build_interleaved_blocks,
    extract_toc_as_text,
    find_figure_by_number,
)

__all__ = [
    "norm",
    "build_interleaved_blocks",
    "extract_toc_as_text",
    "find_figure_by_number",
]
