from __future__ import annotations

import base64
import json
import re
import os
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any

from django.conf import settings
from apps.common.files import normalized_path_exists
from django.core.files.storage import default_storage
from openai import OpenAI

logger = logging.getLogger("grading")

MATH_SOLVING_PROMPT = """
Bạn là một giáo viên Toán Việt Nam xuất sắc với 20 năm kinh nghiệm, chuyên gia trong việc giải toán step-by-step một cách chi tiết và dễ hiểu.

**NHIỆM VỤ:** Phân tích ảnh câu hỏi toán và đưa ra lời giải chi tiết theo format JSON được yêu cầu.

### **QUY TRÌNH GIẢI TOÁN**

**Bước 1: Đọc và Phân Tích Đề Bài**
- Đọc kỹ toàn bộ nội dung câu hỏi trong ảnh
- **QUAN TRỌNG**: Tìm và xác định TỔNG ĐIỂM của câu hỏi trong ảnh:
  - Tìm các ký hiệu như "(2 điểm)", "(3đ)", "2đ", "[4 points]", v.v.
  - Nếu KHÔNG tìm thấy điểm số nào trong ảnh → mặc định là 1 điểm
  - Nếu có nhiều phần con (a, b, c...) → tổng điểm là tổng các phần
- Xác định dạng bài toán, yêu cầu cụ thể
- Ghi nhận các điều kiện, giả thiết, dữ liệu cho trước

**Bước 2: Lập Kế Hoạch Giải**
- Xác định phương pháp, công thức, định lý cần sử dụng
- Sắp xếp thứ tự các bước giải logic

**Bước 3: Giải Chi Tiết Từng Bước**
- Trình bày từng bước một cách rõ ràng
- Giải thích lý do tại sao sử dụng công thức/phương pháp đó
- Tính toán chính xác, kiểm tra kết quả trung gian

**Bước 4: Kết Luận và Kiểm Tra**
- Đưa ra đáp án cuối cùng
- Kiểm tra tính hợp lý của kết quả
- Đối chiếu với yêu cầu đề bài

### **PHÂN ĐIỂM CHI TIẾT**
- **Mỗi bước quan trọng** được gán điểm dựa trên:
  - Mức độ khó của phép tính/lập luận
  - Tầm quan trọng trong chuỗi giải bài
  - Khả năng ảnh hưởng đến kết quả cuối
- **Điểm tối đa:** Sử dụng TỔNG ĐIỂM đã tìm thấy trong ảnh câu hỏi (mặc định 1 nếu không tìm thấy)

### **YÊU CẦU OUTPUT JSON**

Bạn phải trả về một đối tượng JSON duy nhất với cấu trúc chính xác như sau:

```json
{
  "answer": "Đáp án cuối cùng của bài toán",
  "steps": [
    {
      "step_number": 1,
      "description": "Mô tả ngắn gọn",
      "content": "Nội dung với LaTeX format. VD: Giải phương trình $ax^2 + bx + c = 0$ ta có: $$\\Delta = b^2 - 4ac$$",
      "points": 0.5
    },
    {
      "step_number": 2,
      "description": "Mô tả ngắn gọn",
      "content": "Tiếp tục với LaTeX. VD: Do $\\Delta > 0$ nên phương trình có 2 nghiệm phân biệt: $$x_{1,2} = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}$$",
      "points": 1.5
    }
  ],
  "total_points": 2.0
}
```

**LƯU Ý QUAN TRỌNG:**
- Nội dung phải bằng tiếng Việt
- **QUAN TRỌNG**: Tất cả công thức toán học PHẢI được viết bằng LaTeX format:
- **VÍ DỤ CHUẨN**: "Thay vào công thức: $S = \\frac{1}{2} \\times a \\times h = \\frac{1}{2} \\times 6 \\times 4 = 12$"
- Mỗi bước phải logic và dễ hiểu
- `total_points`: Sử dụng điểm số tìm thấy trong ảnh câu hỏi (mặc định 1.0 nếu không tìm thấy)
- Tổng điểm của tất cả các bước phải bằng total_points
- Chỉ trả về JSON, không có text thêm nào khác
"""


def _read_image_bytes(path_or_key: str) -> bytes:
	"""Load image bytes from storage if key exists, otherwise filesystem.

	Raises FileNotFoundError if neither source has the object.
	"""
	# Prefer storage when present (S3/Supabase)
	try:
		if default_storage.exists(path_or_key):
			with default_storage.open(path_or_key, "rb") as fh:
				return fh.read()
	except Exception:
		# fall back to filesystem path
		pass

	p = Path(path_or_key)
	if not p.exists():
		raise FileNotFoundError(f"Image not found: {path_or_key}")
	with p.open("rb") as f:
		return f.read()


def _encode_image(image_path: str) -> str:
	return base64.b64encode(_read_image_bytes(image_path)).decode("utf-8")


def _get_mime(path: str) -> str:
	ext = Path(path).suffix.lower()
	return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "image/jpeg")


def _latex_like_to_unicode(text: str | None) -> str | None:
	"""Lightweight conversion of LaTeX-like fragments to readable Unicode/plain text.

	Removes math delimiters and maps common tokens (\\times, \\pm, \\sqrt, ...).
	"""
	if text is None:
		return None

	result = text
	# Strip math delimiters: $...$, $$...$$, \( ... \), \[ ... \]
	result = re.sub(r"\$\$?([^$]+)\$\$?", r"\1", result)
	result = re.sub(r"\\\((.*?)\\\)", r"\1", result)
	result = re.sub(r"\\\[(.*?)\\\]", r"\1", result)

	# Remove \left and \right, replace braces with parentheses for readability
	result = re.sub(r"\\left|\\right", "", result)
	result = result.replace("{", "(").replace("}", ")")

	# Token mappings
	mapping = {
		"\\times": "×",
		"\\cdot": "·",
		"\\pm": "±",
		"\\le": "≤",
		"\\ge": "≥",
		"\\neq": "≠",
		"\\approx": "≈",
		"\\infty": "∞",
		"\\sqrt": "√",
		"\\Delta": "Δ",
		"\\delta": "δ",
		"\\alpha": "α",
		"\\beta": "β",
		"\\gamma": "γ",
		"\\pi": "π",
	}
	for k, v in mapping.items():
		result = result.replace(k, v)

	# Simple fractions: \frac{a}{b} -> (a)/(b)
	result = re.sub(r"\\frac\s*\{([^}]+)\}\s*\{([^}]+)\}", r"(\1)/(\2)", result)

	# Normalize sqrt{...} -> √(...)
	result = re.sub(r"\\sqrt\s*\{([^}]+)\}", r"√(\1)", result)

	# Collapse multiple spaces
	result = re.sub(r"\s+", " ", result).strip()
	return result

def solve_question(question_image_paths: List[str]) -> Dict[str, Any]:
	run_id = str(uuid.uuid4())
	model_name = os.getenv("OPENAI_SOLVER_MODEL", "gpt-4o-mini")
	
	logger.debug("run=%s start solve_question model=%s image_count=%d", run_id, model_name, len(question_image_paths))
	
	api_key = getattr(settings, "OPENAI_API_KEY", None)
	if not api_key:
		raise RuntimeError("OPENAI_API_KEY is not configured")
	client = OpenAI(api_key=api_key)

	messages: List[Dict[str, Any]] = [
		{"role": "system", "content": MATH_SOLVING_PROMPT},
		{"role": "user", "content": [{"type": "text", "text": "Hãy giải bài toán trong ảnh theo format JSON. LƯU Ý: Không dùng LaTeX, hãy dùng văn bản/Unicode dễ đọc cho công thức."}]},
	]

	# attach images
	for p in question_image_paths:
		# Load from storage or filesystem; raise if missing
		try:
			b64 = _encode_image(p)
		except FileNotFoundError:
			raise FileNotFoundError(f"Question image not found: {p}")
		mime = _get_mime(p)
		messages[1]["content"].append({
			"type": "image_url",
			"image_url": {"url": f"data:{mime};base64,{b64}", "detail": "high"}
		})

	logger.debug("run=%s image_paths=%s", run_id, [str(p) for p in question_image_paths])

	resp = client.chat.completions.create(
		model=model_name,
		messages=messages,
		response_format={"type": "json_object"},
	)

	# Extract token usage
	usage = resp.usage
	if usage:
		prompt_tokens = usage.prompt_tokens
		completion_tokens = usage.completion_tokens
		total_tokens = usage.total_tokens
		
		# GPT-4o-mini pricing: $0.150 per 1M input tokens, $0.600 per 1M output tokens
		# Adjust if using different model
		input_cost = (prompt_tokens / 1_000_000) * 0.150
		output_cost = (completion_tokens / 1_000_000) * 0.600
		total_cost = input_cost + output_cost
		
		logger.info(
			"run=%s USAGE model=%s prompt_tokens=%d completion_tokens=%d total_tokens=%d input_cost=$%.6f output_cost=$%.6f total_cost=$%.6f",
			run_id, model_name, prompt_tokens, completion_tokens, total_tokens,
			input_cost, output_cost, total_cost
		)
	else:
		logger.warning("run=%s No usage data in OpenAI response", run_id)

	data = json.loads(resp.choices[0].message.content)
	logger.debug("run=%s parsed_solution=%s", run_id, {k: v for k, v in data.items() if k != "steps"})
	
	# Normalize fields
	answer = _latex_like_to_unicode(data.get("answer"))
	steps_raw = data.get("steps", [])
	steps: List[Dict[str, Any]] = []
	for s in steps_raw:
		if not isinstance(s, dict):
			continue
		item = dict(s)
		item["description"] = _latex_like_to_unicode(item.get("description"))
		item["content"] = _latex_like_to_unicode(item.get("content"))
		steps.append(item)
	total_points = data.get("total_points", sum(s.get("points", 0) for s in steps))
	return {
		"answer": answer,
		"steps": steps,
		"total_points": total_points,
		"generated_at": datetime.now(timezone.utc).isoformat(),
	}


