import os
import base64
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from openai import AsyncOpenAI, OpenAI
from core.prompts import OPENAI_MATH_SOLVING_PROMPT

# Setup logging
logger = logging.getLogger(__name__)

class OpenAISolver:
    """
    A specialized OpenAI model for solving math questions step-by-step.
    Uses GPT-5 Mini for detailed mathematical problem solving.
    """


    def __init__(self, api_key: str, model_name: str):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self.client = OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name
        logger.info(f"OpenAISolver initialized with model: {self.model_name}")

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

    async def solve_question(self, question_image_paths: List[str]) -> Dict[str, Any]:
        """
        Solves a math question by analyzing the question images using GPT-5 Mini.

        Args:
            question_image_paths: List of paths to question images

        Returns:
            Dictionary containing solution with answer, steps, and points
        """
        logger.info(f"Solving question with {len(question_image_paths)} images using GPT-5 Mini")

        try:
            # Prepare messages for OpenAI API
            messages = [
                {
                    "role": "system",
                    "content": OPENAI_MATH_SOLVING_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Hãy giải bài toán trong ảnh theo format JSON được yêu cầu."
                        }
                    ]
                }
            ]

            # Add images to the user message
            for img_path in question_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Question image not found: {img_path}")

                # Encode image to base64
                base64_image = self._encode_image(img_path)
                mime_type = self._get_image_mime_type(img_path)

                messages[1]["content"].append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type};base64,{base64_image}",
                        "detail": "high"
                    }
                })

            # Make API call to GPT-5 Mini
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={"type": "json_object"}
            )

            # Parse JSON response
            result_json = json.loads(response.choices[0].message.content)

            # Add metadata
            result_json["solved_at"] = datetime.now().isoformat()
            result_json["model_used"] = self.model_name

            # Ensure required fields exist with defaults
            if "total_points" not in result_json:
                result_json["total_points"] = 1.0

            logger.info(f"Successfully solved question with {len(result_json.get('steps', []))} steps, total points: {result_json.get('total_points', 0)}")
            return result_json

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {
                "answer": "Lỗi: Không thể phân tích phản hồi từ AI",
                "steps": [],
                "total_points": 1.0,
                "error": True
            }
        except Exception as e:
            logger.error(f"Question solving failed: {e}")
            return {
                "answer": "Lỗi: Không thể giải bài toán",
                "steps": [],
                "total_points": 1.0,
                "error": True
            }

    async def solve_questions_batch(self, questions_data: List[Dict]) -> List[Dict[str, Any]]:
        """
        Solves multiple questions concurrently with rate limiting.

        Args:
            questions_data: List of dicts with 'question_id' and 'image_paths' keys

        Returns:
            List of solution dictionaries with question_id included
        """
        if not questions_data:
            return []

        logger.info(f"Starting batch solving for {len(questions_data)} questions")

        # Limit concurrent requests to avoid API rate limits
        semaphore = asyncio.Semaphore(10)  # Max 10 concurrent requests for GPT-5 Mini

        async def solve_single_question(question_data):
            async with semaphore:
                question_id = question_data['question_id']
                image_paths = question_data['image_paths']

                logger.info(f"Solving question ID {question_id}")
                solution = await self.solve_question(image_paths)
                solution['question_id'] = question_id

                return solution

        # Execute all solving tasks concurrently
        tasks = [solve_single_question(q_data) for q_data in questions_data]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Handle exceptions in results
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Question {questions_data[i]['question_id']} solving failed: {result}")
                processed_results.append({
                    "question_id": questions_data[i]['question_id'],
                    "answer": "Lỗi: Không thể giải bài toán",
                    "steps": [],
                    "total_points": 1.0,
                    "error": True
                })
            else:
                processed_results.append(result)

        logger.info(f"Completed batch solving for {len(questions_data)} questions")
        return processed_results