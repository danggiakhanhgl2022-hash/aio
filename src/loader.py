import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Any, Optional

import fitz  # PyMuPDF

from .config import CHUNK_SIZE, CHUNK_OVERLAP, PDF_RENDER_SCALE, FIGURE_CROP_HEIGHT
from .utils import clean_text_keep_newlines, chunk_text, norm
from .vision import analyze_image_with_ollama


@dataclass
class TextChunk:
    chunk_id: int
    source_name: str
    page: int
    text: str
    kind: str = "text"


@dataclass
class FigureRecord:
    figure_id: int
    source_name: str
    page: int
    caption: str
    image_path: str
    nearby_text: str = ""
    visible_text: List[str] = field(default_factory=list)
    objects: List[str] = field(default_factory=list)
    flow: List[str] = field(default_factory=list)
    summary: str = ""
    vision_error: str = ""


@dataclass
class NotebookData:
    sources: List[Dict[str, Any]] = field(default_factory=list)
    pages: List[Dict[str, Any]] = field(default_factory=list)
    chunks: List[TextChunk] = field(default_factory=list)
    figures: List[FigureRecord] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.get("text", "") for p in self.pages if p.get("text"))


CAPTION_RE = re.compile(r"(Hình|Hinh|Figure|Fig\.?)\s*(\d+)\s*[:.\-]\s*(.+)", flags=re.I)


def _safe_filename(name: str) -> str:
    name = re.sub(r"[^\w\-.]+", "_", name, flags=re.U)
    return name[:120] or f"file_{uuid.uuid4().hex}"


def _line_near_caption(page_text: str, caption: str, before: int = 8, after: int = 8) -> str:
    lines = [ln.strip() for ln in page_text.splitlines() if ln.strip()]
    if not lines:
        return ""

    cap_norm = norm(caption)
    idx = -1
    for i, line in enumerate(lines):
        if cap_norm and cap_norm[:40] in norm(line):
            idx = i
            break

    if idx == -1:
        return "\n".join(lines[:20])

    s = max(0, idx - before)
    e = min(len(lines), idx + after + 1)
    return "\n".join(lines[s:e])


def _find_caption_blocks(page) -> List[Dict[str, Any]]:
    """
    Tìm caption có vị trí bbox để crop hình.
    """
    result = []
    blocks = page.get_text("blocks") or []
    for b in blocks:
        if len(b) < 5:
            continue
        x0, y0, x1, y1, text = b[:5]
        text_clean = " ".join(str(text).split())
        m = CAPTION_RE.search(text_clean)
        if m:
            fig_id = int(m.group(2))
            caption = f"Hình {fig_id}: {m.group(3).strip()}"
            result.append(
                {
                    "figure_id": fig_id,
                    "caption": caption,
                    "bbox": fitz.Rect(x0, y0, x1, y1),
                    "raw": text_clean,
                }
            )
    return result


def _crop_figure_above_caption(page, caption_bbox: fitz.Rect, out_path: Path):
    """
    Crop vùng phía trên caption. Nếu crop quá nhỏ thì render full page.
    """
    rect = page.rect
    top = max(0, caption_bbox.y0 - FIGURE_CROP_HEIGHT)
    bottom = min(rect.height, caption_bbox.y1 + 25)
    clip = fitz.Rect(0, top, rect.width, bottom)

    if clip.height < 120:
        clip = rect

    matrix = fitz.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE)
    pix = page.get_pixmap(matrix=matrix, clip=clip, alpha=False)
    pix.save(str(out_path))


def _render_page_image(page, out_path: Path):
    matrix = fitz.Matrix(PDF_RENDER_SCALE, PDF_RENDER_SCALE)
    pix = page.get_pixmap(matrix=matrix, alpha=False)
    pix.save(str(out_path))


def load_pdf(pdf_path: Path, figure_dir: Path, use_vision: bool = True) -> NotebookData:
    data = NotebookData()
    source_name = pdf_path.name
    figure_dir.mkdir(parents=True, exist_ok=True)

    doc = fitz.open(str(pdf_path))
    next_chunk_id = 1
    seen_fig_ids = set()

    for page_index in range(len(doc)):
        page = doc[page_index]
        page_no = page_index + 1
        raw_text = page.get_text("text") or ""
        text = clean_text_keep_newlines(raw_text)

        data.pages.append(
            {
                "source_name": source_name,
                "page": page_no,
                "text": text,
            }
        )

        # Text chunks
        for ch in chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP):
            data.chunks.append(
                TextChunk(
                    chunk_id=next_chunk_id,
                    source_name=source_name,
                    page=page_no,
                    text=ch,
                )
            )
            next_chunk_id += 1

        # Figures by caption
        caption_blocks = _find_caption_blocks(page)
        for cb in caption_blocks:
            fig_id = cb["figure_id"]
            if fig_id in seen_fig_ids:
                continue

            seen_fig_ids.add(fig_id)
            img_path = figure_dir / f"{pdf_path.stem}_figure_{fig_id}_page_{page_no}.png"
            _crop_figure_above_caption(page, cb["bbox"], img_path)

            caption = cb["caption"]
            nearby = _line_near_caption(text, caption)

            vision = {}
            if use_vision:
                vision = analyze_image_with_ollama(str(img_path), caption=caption, nearby_text=nearby)

            data.figures.append(
                FigureRecord(
                    figure_id=fig_id,
                    source_name=source_name,
                    page=page_no,
                    caption=caption,
                    image_path=str(img_path),
                    nearby_text=nearby,
                    visible_text=vision.get("visible_text", []) if vision else [],
                    objects=vision.get("objects", []) if vision else [],
                    flow=vision.get("flow", []) if vision else [],
                    summary=vision.get("summary", "") if vision else "",
                    vision_error=vision.get("error", "") if vision else "",
                )
            )

    data.sources.append(
        {
            "name": source_name,
            "type": "PDF",
            "pages": len(doc),
            "chunks": len(data.chunks),
            "figures": len(data.figures),
            "text_preview": "\n".join(p["text"] for p in data.pages[:2])[:3000],
        }
    )

    return data


def load_txt(txt_path: Path) -> NotebookData:
    data = NotebookData()
    source_name = txt_path.name
    text = clean_text_keep_newlines(txt_path.read_text(encoding="utf-8", errors="ignore"))

    data.pages.append({"source_name": source_name, "page": 1, "text": text})

    for idx, ch in enumerate(chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP), start=1):
        data.chunks.append(TextChunk(chunk_id=idx, source_name=source_name, page=1, text=ch))

    data.sources.append(
        {
            "name": source_name,
            "type": "TXT",
            "pages": 1,
            "chunks": len(data.chunks),
            "figures": 0,
            "text_preview": text[:3000],
        }
    )
    return data


def merge_notebooks(items: List[NotebookData]) -> NotebookData:
    merged = NotebookData()
    chunk_id = 1

    for item in items:
        merged.sources.extend(item.sources)
        merged.pages.extend(item.pages)
        merged.figures.extend(item.figures)

        for ch in item.chunks:
            ch.chunk_id = chunk_id
            merged.chunks.append(ch)
            chunk_id += 1

    # sort figure id nếu có
    merged.figures.sort(key=lambda f: (f.figure_id, f.page))
    return merged


def load_files(saved_paths: List[Path], figure_dir: Path, use_vision: bool = True) -> NotebookData:
    notebooks = []
    for p in saved_paths:
        suffix = p.suffix.lower()
        if suffix == ".pdf":
            notebooks.append(load_pdf(p, figure_dir=figure_dir, use_vision=use_vision))
        elif suffix in [".txt", ".md"]:
            notebooks.append(load_txt(p))
    return merge_notebooks(notebooks)
