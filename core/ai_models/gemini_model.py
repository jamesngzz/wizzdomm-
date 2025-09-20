import os
import base64
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from google import genai
from google.genai import types

from .base_model import BaseGradingModel
from core.llm_logger import log_llm_call, SERVICE_VISION_GRADING
from core.prompts import GEMINI_VISION_GRADING_PROMPT

# Setup logging
logger = logging.getLogger(__name__)

class GeminiModel(BaseGradingModel):
    """
    An implementation of the BaseGradingModel using Google's Gemini Vision models.
    """


    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("Gemini API key is required.")
        self.client = genai.Client(api_key=api_key)
        self.model_name = model_name
        logger.info(f"GeminiModel initialized with model: {self.model_name}")

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64."""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise

    def _get_image_mime_type(self, image_path: str) -> str:
        """Determine MIME type from file extension."""
        ext = Path(image_path).suffix.lower()
        return {'.jpg': 'image/jpeg', '.jpeg': 'image/jpeg', '.png': 'image/png'}.get(ext, 'image/jpeg')

    def grade_image_pair(self, question_image_paths: List[str], answer_image_paths: List[str],
                        clarify: str = None, previous_grading: Dict[str, Any] = None,
                        solution: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Grades a student's answer by analyzing question and answer images using Gemini's API.

        Args:
            solution: AI-generated solution with steps containing description and content
        """
        logger.info(f"Grading with Gemini: {len(question_image_paths)} question images vs {len(answer_image_paths)} answer images.")
        logger.info(f"Question image paths: {question_image_paths}")
        logger.info(f"Answer image paths: {answer_image_paths}")

        try:
            # Build the initial message
            initial_text = "Hãy chấm bài tự luận toán của học sinh."

            # Add solution reference if provided
            if solution and solution.get('steps'):
                initial_text += "\n\n**LỜI GIẢI THAM KHẢO:**\n"
                steps = solution.get('steps', [])
                for i, step in enumerate(steps, 1):
                    description = step.get('description', f'Bước {i}')
                    content = step.get('content', '')
                    initial_text += f"Bước {i}: {description}\n{content}\n\n"

            # Add clarification context if re-grading
            if clarify and previous_grading:
                initial_text += f"\n\n**CHẤM LẠI VỚI CLARIFICATION:**\n"
                initial_text += f"Thầy cô clarify: {clarify}\n"
                initial_text += f"Lần chấm trước kết quả là: Đúng={previous_grading.get('is_correct', 'N/A')}, "
                initial_text += f"Lỗi='{previous_grading.get('error_description', 'N/A')}'\n"
                initial_text += f"Dựa vào clarification này, hãy chấm lại câu hỏi với sự chú ý đặc biệt đến phần thầy cô đã chỉ ra."

            # Prepare parts list - text should be Part.from_text()
            parts = [types.Part.from_text(text=initial_text)]

            # Add question images
            for img_path in question_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Question image not found: {img_path}")

                # Read image as bytes for Gemini
                with open(img_path, "rb") as f:
                    image_data = f.read()

                parts.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=self._get_image_mime_type(img_path)
                ))

            # Add answer images
            for img_path in answer_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Answer image not found: {img_path}")

                # Read image as bytes for Gemini
                with open(img_path, "rb") as f:
                    image_data = f.read()

                parts.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=self._get_image_mime_type(img_path)
                ))

            # Make API call to Gemini
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=parts
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=GEMINI_VISION_GRADING_PROMPT,
                    temperature=0,
                    response_mime_type="application/json"
                )
            )

            # Log the response for debugging
            logger.info(f"Gemini API response received for grading")

            # Check if response has text content
            if not response or not response.text:
                logger.error("Gemini API returned empty response")
                return {
                    "is_correct": False,
                    "critical_errors": [{"description": "AI response was empty", "phrases": ["Empty response"]}],
                    "part_errors": [],
                    "partial_credit": False
                }

            # Parse JSON response
            try:
                result_json = json.loads(response.text)
                return result_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed, raw response: {response.text[:200]}...")
                return {
                    "is_correct": False,
                    "critical_errors": [{"description": "Failed to parse AI response", "phrases": ["Parse error"]}],
                    "part_errors": [],
                    "partial_credit": False
                }

        except json.JSONDecodeError as e:
            logger.error(f"Gemini response JSON parsing failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini grading failed: {e}")
            raise

    async def _grade_image_pair_async(self, question_image_paths: List[str], answer_image_paths: List[str],
                                     clarify: str = None, previous_grading: Dict[str, Any] = None,
                                     solution: Dict[str, Any] = None) -> Dict[str, Any]:
        """Async version of grade_image_pair for batch processing"""
        logger.info(f"Async grading with Gemini: {len(question_image_paths)} question images vs {len(answer_image_paths)} answer images.")

        try:
            # Build the initial message
            initial_text = "Hãy chấm bài tự luận toán của học sinh."

            # Add solution reference if provided
            if solution and solution.get('steps'):
                initial_text += "\n\n**LỜI GIẢI THAM KHẢO:**\n"
                steps = solution.get('steps', [])
                for i, step in enumerate(steps, 1):
                    description = step.get('description', f'Bước {i}')
                    content = step.get('content', '')
                    initial_text += f"Bước {i}: {description}\n{content}\n\n"

            # Add clarification context if re-grading
            if clarify and previous_grading:
                initial_text += f"\n\n**CHẤM LẠI VỚI CLARIFICATION:**\n"
                initial_text += f"Thầy cô clarify: {clarify}\n"
                initial_text += f"Lần chấm trước kết quả là: Đúng={previous_grading.get('is_correct', 'N/A')}, "
                initial_text += f"Lỗi='{previous_grading.get('error_description', 'N/A')}'\n"
                initial_text += f"Dựa vào clarification này, hãy chấm lại câu hỏi với sự chú ý đặc biệt đến phần thầy cô đã chỉ ra."

            # Prepare parts list - text should be Part.from_text()
            parts = [types.Part.from_text(text=initial_text)]

            # Add question images
            for img_path in question_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Question image not found: {img_path}")

                # Read image as bytes for Gemini
                with open(img_path, "rb") as f:
                    image_data = f.read()

                parts.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=self._get_image_mime_type(img_path)
                ))

            # Add answer images
            for img_path in answer_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Answer image not found: {img_path}")

                # Read image as bytes for Gemini
                with open(img_path, "rb") as f:
                    image_data = f.read()

                parts.append(types.Part.from_bytes(
                    data=image_data,
                    mime_type=self._get_image_mime_type(img_path)
                ))

            # Note: Gemini client might not have async support yet, so we'll use sync in async wrapper
            # This can be updated when Gemini adds proper async support
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[
                    types.Content(
                        role="user",
                        parts=parts
                    )
                ],
                config=types.GenerateContentConfig(
                    system_instruction=GEMINI_VISION_GRADING_PROMPT,
                    temperature=0,
                    response_mime_type="application/json"
                )
            )

            # Check if response has text content
            if not response or not response.text:
                logger.error("Gemini API returned empty response in async")
                return {
                    "is_correct": False,
                    "critical_errors": [{"description": "AI response was empty", "phrases": ["Empty response"]}],
                    "part_errors": [],
                    "partial_credit": False
                }

            try:
                result_json = json.loads(response.text)
                return result_json
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed in async, raw response: {response.text[:200]}...")
                return {
                    "is_correct": False,
                    "critical_errors": [{"description": "Failed to parse AI response", "phrases": ["Parse error"]}],
                    "part_errors": [],
                    "partial_credit": False
                }

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {"is_correct": False, "critical_errors": [{"description": "Failed to parse AI response", "phrases": []}], "part_errors": [], "partial_credit": False}
        except Exception as e:
            logger.error(f"Async API request failed: {e}")
            return {"is_correct": False, "critical_errors": [{"description": f"API error: {str(e)}", "phrases": []}], "part_errors": [], "partial_credit": False}

    def grade_batch(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Override base method to use async processing with concurrency limit"""
        if not items:
            return []

        logger.info(f"Starting async batch grading for {len(items)} items with max 10 concurrent requests")
        return asyncio.run(self._grade_batch_async(items))

    async def _grade_batch_async(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """Async batch processing with concurrency limit"""
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests

        async def process_item(item):
            async with semaphore:
                return await self._grade_image_pair_async(
                    question_image_paths=item['question_image_paths'],
                    answer_image_paths=item['answer_image_paths'],
                    clarify=item.get('clarify'),
                    previous_grading=item.get('previous_grading'),
                    solution=item.get('solution')
                )

        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks)

        logger.info(f"Async batch grading completed for {len(items)} items")
        return results