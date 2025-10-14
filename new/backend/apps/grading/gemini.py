import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional

from django.conf import settings
import logging
import uuid
from google import genai
from google.genai import types

from .prompts import GEMINI_VISION_GRADING_PROMPT


class GeminiGrader:
    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GEMINI_API_KEY", None)
        self.model_name = model_name or getattr(settings, "GEMINI_MODEL_NAME", "gemini-2.5-flash")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required")
        self.client = genai.Client(api_key=self.api_key)
        self.logger = logging.getLogger("grading")

    @staticmethod
    def _mime(path: str) -> str:
        ext = Path(path).suffix.lower()
        return {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "image/jpeg")

    def grade_image_pair(
        self,
        question_image_paths: List[str],
        answer_image_paths: List[str],
        clarify: Optional[str] = None,
        previous_grading: Optional[Dict[str, Any]] = None,
        solution: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        run_id = str(uuid.uuid4())
        self.logger.debug(
            "run=%s start grade_image_pair model=%s q_count=%d a_count=%d clarify=%s has_previous=%s has_solution=%s",
            run_id,
            self.model_name,
            len(question_image_paths or []),
            len(answer_image_paths or []),
            bool(clarify),
            bool(previous_grading),
            bool(solution and solution.get("steps")),
        )
        # Build initial instruction
        initial_text = "Hãy chấm bài tự luận toán của học sinh."
        if solution and solution.get("steps"):
            initial_text += "\n\n**LỜI GIẢI THAM KHẢO:**\n"
            for i, step in enumerate(solution["steps"], 1):
                initial_text += f"Bước {i}: {step.get('description','')}\n{step.get('content','')}\n\n"
        if clarify and previous_grading:
            initial_text += "\n\n**CHẤM LẠI VỚI CLARIFICATION:**\n"
            initial_text += f"Thầy cô clarify: {clarify}\n"

        parts: List[types.Part] = [types.Part.from_text(text=initial_text)]

        for p in question_image_paths:
            if not os.path.exists(p):
                raise FileNotFoundError(f"Question image not found: {p}")
            with open(p, "rb") as f:
                parts.append(types.Part.from_bytes(data=f.read(), mime_type=self._mime(p)))

        for p in answer_image_paths:
            if not os.path.exists(p):
                raise FileNotFoundError(f"Answer image not found: {p}")
            with open(p, "rb") as f:
                parts.append(types.Part.from_bytes(data=f.read(), mime_type=self._mime(p)))

        self.logger.debug(
            "run=%s prompt_preview=%s q_paths=%s a_paths=%s",
            run_id,
            initial_text[:300],
            [str(p) for p in question_image_paths],
            [str(p) for p in answer_image_paths],
        )

        resp = self.client.models.generate_content(
            model=self.model_name,
            contents=[types.Content(role="user", parts=parts)],
            config=types.GenerateContentConfig(
                system_instruction=GEMINI_VISION_GRADING_PROMPT,
                temperature=0,
                response_mime_type="application/json",
            ),
        )

        # Extract token usage metadata
        usage_metadata = getattr(resp, "usage_metadata", None)
        if usage_metadata:
            prompt_tokens = getattr(usage_metadata, "prompt_token_count", 0)
            completion_tokens = getattr(usage_metadata, "candidates_token_count", 0)
            total_tokens = getattr(usage_metadata, "total_token_count", 0)
            
            # Gemini 2.5 Flash pricing (as of 2025): $0.075 per 1M input tokens, $0.30 per 1M output tokens
            input_cost = (prompt_tokens / 1_000_000) * 0.075
            output_cost = (completion_tokens / 1_000_000) * 0.30
            total_cost = input_cost + output_cost
            
            self.logger.info(
                "run=%s USAGE model=%s prompt_tokens=%d completion_tokens=%d total_tokens=%d input_cost=$%.6f output_cost=$%.6f total_cost=$%.6f",
                run_id, self.model_name, prompt_tokens, completion_tokens, total_tokens,
                input_cost, output_cost, total_cost
            )
        else:
            self.logger.warning("run=%s No usage_metadata in response", run_id)

        self.logger.debug("run=%s llm_raw_text=%s", run_id, getattr(resp, "text", "")[:500])

        if not resp or not getattr(resp, "text", ""):
            return {
                "is_correct": False,
                "critical_errors": [{"description": "Empty LLM response", "phrases": ["empty"]}],
                "part_errors": [],
                "partial_credit": False,
            }

        try:
            parsed = json.loads(resp.text)
            self.logger.debug("run=%s parsed_result=%s", run_id, parsed)
            return parsed
        except json.JSONDecodeError:
            self.logger.exception("run=%s parse_error on LLM response", run_id)
            return {
                "is_correct": False,
                "critical_errors": [{"description": "Invalid JSON from LLM", "phrases": ["parse error"]}],
                "part_errors": [],
                "partial_credit": False,
            }



