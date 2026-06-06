import base64
import json
import re
from pathlib import Path
from typing import Dict, Any

from .config import VISION_MODEL


def _encode_image(image_path: str) -> str:
    data = Path(image_path).read_bytes()
    return base64.b64encode(data).decode("utf-8")


def _extract_json(text: str) -> Dict[str, Any]:
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    return {
        "visible_text": [],
        "summary": text[:1200],
        "flow": [],
        "objects": [],
    }


def analyze_image_with_ollama(image_path: str, caption: str = "", nearby_text: str = "") -> Dict[str, Any]:
    """
    Đọc hình bằng Ollama vision model.
    Nếu máy chưa có llava:latest hoặc model lỗi, trả error nhưng app vẫn chạy.
    """
    try:
        import ollama
    except Exception as e:
        return {
            "visible_text": [],
            "summary": "",
            "flow": [],
            "objects": [],
            "error": f"Chưa cài thư viện ollama: {e}",
        }

    prompt = f"""
Bạn là module đọc hình trong tài liệu PDF.

Nhiệm vụ:
1. Đọc chữ/nhãn nhìn thấy trong hình.
2. Mô tả đúng nội dung hình.
3. Nếu là sơ đồ, mô tả luồng xử lý.
4. Không bịa ngoài hình và caption.

CAPTION:
{caption}

TEXT GẦN HÌNH TRONG PDF:
{nearby_text[:1500]}

Trả về JSON hợp lệ, không markdown:
{{
  "visible_text": ["..."],
  "objects": ["..."],
  "flow": ["..."],
  "summary": "..."
}}
"""

    try:
        img_b64 = _encode_image(image_path)
        res = ollama.chat(
            model=VISION_MODEL,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                    "images": [img_b64],
                }
            ],
            options={"temperature": 0},
        )
        content = res.get("message", {}).get("content", "")
        data = _extract_json(content)
        data.setdefault("visible_text", [])
        data.setdefault("objects", [])
        data.setdefault("flow", [])
        data.setdefault("summary", "")
        data["error"] = ""
        return data

    except Exception as e:
        return {
            "visible_text": [],
            "summary": "",
            "flow": [],
            "objects": [],
            "error": str(e),
        }
