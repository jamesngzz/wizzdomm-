import os
import base64
import json
import logging
import asyncio
from pathlib import Path
from typing import List, Dict, Any

from openai import AsyncOpenAI, OpenAI

from .base_model import BaseGradingModel
from core.llm_logger import log_llm_call, SERVICE_VISION_GRADING

# Setup logging
logger = logging.getLogger(__name__)

class OpenAIModel(BaseGradingModel):
    """
    An implementation of the BaseGradingModel using OpenAI's GPT Vision models.
    """
    
    # The detailed prompt is now part of this model-specific implementation.
    VISION_GRADING_PROMPT = """
Một giáo viên Toán Việt Nam tài giỏi với 20 năm kinh nghiệm, sở trường của bạn là phân tích sâu sắc logic giải bài của học sinh và đưa ra những nhận xét chính xác, công tâm.
**IMAGES INPUT:**
1.  **ẢNH ĐỀ BÀI:** Nội dung câu hỏi.
2.  **ẢNH BÀI LÀM:** Lời giải viết tay của học sinh.

### **TRIẾT LÝ VÀ QUY TRÌNH CHẤM BÀI**
**Bước 1: Đọc Hiểu Toàn Diện**
Đầu tiên, đọc kỹ **ẢNH ĐỀ BÀI**, nắm vững yêu cầu. 
Sau đó, đọc lướt toàn bộ **ẢNH BÀI LÀM** để hiểu luồng tư duy tổng thể của học sinh TRƯỚC KHI đi vào chi tiết. 
Đừng vội vàng phán xét ngay từ lỗi sai đầu tiên.
**Bước 2: Phân tích Logic và Tìm "Lỗi Gốc" (Root Cause Analysis)**
Đây là bước quan trọng nhất. Hãy dò theo từng bước lập luận của học sinh:
*   **Hướng đi có đúng không?** Học sinh có chọn đúng phương pháp, định lý, công thức để giải quyết vấn đề không?
*   **Thực thi có chính xác không?** Trong quá trình biến đổi, tính toán, học sinh có mắc lỗi không? (ví dụ: chuyển vế sai dấu, tính toán sai, áp dụng sai điều kiện).
*   **Tìm Lỗi Gốc:** Nếu có nhiều lỗi sai, hãy tập trung vào **lỗi sai đầu tiên và cơ bản nhất** đã gây ra chuỗi sai lầm sau đó. Ví dụ, nếu học sinh tính sai Delta ngay từ đầu, dẫn đến toàn bộ phần tìm nghiệm phía sau đều sai, thì "lỗi gốc" là "Tính sai biệt thức Delta".
*   **Công nhận nỗ lực:** Nếu học sinh có hướng đi đúng nhưng gặp lỗi tính toán nhỏ, hãy ghi nhận phần tư duy đúng đắn đó.

### **TIÊU CHÍ ĐÁNH GIÁ**
✅ ĐÚNG: Khi **phương pháp + đáp án** đều đúng. Lời giải hợp lý về mặt toán học, không chứa lỗi logic nghiêm trọng.
🔄 ĐIỂM MỘT PHẦN: Phương pháp đúng hoặc đáp án đúng nhưng sai sót nhỏ trong tính toán, hoặc các lỗi không đáng kể.
❌ SAI: Phương pháp sai hoặc đáp án sai hoặc đúng một cách "may mắn" nhưng có lỗ hổng logic nghiệm trọng.
❌ KHÔNG LÀM BÀI: Bỏ trống hoặc bài làm không đọc được.

### **YÊU CẦU OUTPUT (BẮT BUỘC)**

Bạn phải trả về một đối tượng JSON duy nhất với cấu trúc chính xác như sau:

```json
{
  "is_correct": true/false,
  "confidence": float, (từ 0 đến 1) #Mức độ tự tin của Model khi chấm bài
  "error_description": "Giải thích chi tiết về các lỗi", #Nếu đúng và không có lỗi nào cả thì trả về NULL
  "error_phrases":"Lỗi sai học sinh cụ thể" (tối đa 15 từ một ý, tối đa 3 ý) Ví dụ: ["Mâu thuẫn logic: khẳng định (x-3)^2020+(2y+6)^2022>0 rồi lại suy ra =0", "Đặt điều kiện cho phương trình chứa căn sai, phải là ... chứ không là ...",...]
  "partial_credit": true/false #Trong quá trình làm bài tồn tại những bước đúng (Ví dụ logic giải bài gồm 4 bước và đúng hai bước đầu)
}
"""

    def __init__(self, api_key: str, model_name: str = "gpt-4o"):
        if not api_key:
            raise ValueError("OpenAI API key is required.")
        self.client = OpenAI(api_key=api_key)
        self.async_client = AsyncOpenAI(api_key=api_key)
        self.model_name = model_name
        logger.info(f"OpenAIModel initialized with model: {self.model_name}")

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

    def grade_image_pair(self, question_image_paths: List[str], answer_image_paths: List[str]) -> Dict[str, Any]:
        """
        Grades a student's answer by analyzing question and answer images using OpenAI's API.
        """
        logger.info(f"Grading with OpenAI: {len(question_image_paths)} question images vs {len(answer_image_paths)} answer images.")
        logger.info(f"Question image paths: {question_image_paths}")
        logger.info(f"Answer image paths: {answer_image_paths}")
        
        try:
            message_content = [{"type": "text", "text": "Hãy chấm bài tự luận toán của học sinh."}]

            # Add question images
            for img_path in question_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Question image not found: {img_path}")
                b64_image = self._encode_image(img_path)
                mime_type = self._get_image_mime_type(img_path)
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64_image}", "detail": "high"}
                })

            # Add answer images
            for img_path in answer_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Answer image not found: {img_path}")
                b64_image = self._encode_image(img_path)
                mime_type = self._get_image_mime_type(img_path)
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64_image}", "detail": "high"}
                })

            messages = [
                {"role": "system", "content": self.VISION_GRADING_PROMPT},
                {"role": "user", "content": message_content}
            ]

            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_completion_tokens=5000,
                response_format={"type": "json_object"}
            )

            log_llm_call(response, self.model_name, SERVICE_VISION_GRADING)
            
            result_json = json.loads(response.choices[0].message.content)
            return result_json

        except json.JSONDecodeError as e:
            logger.error(f"OpenAI response JSON parsing failed: {e}")
            raise
        except Exception as e:
            logger.error(f"OpenAI grading failed: {e}")
            raise

    async def _grade_image_pair_async(self, question_image_paths: List[str], answer_image_paths: List[str]) -> Dict[str, Any]:
        """Async version of grade_image_pair for batch processing"""
        logger.info(f"Async grading with OpenAI: {len(question_image_paths)} question images vs {len(answer_image_paths)} answer images.")
        
        try:
            message_content = [{"type": "text", "text": "Hãy chấm bài tự luận toán của học sinh."}]

            # Add question images
            for img_path in question_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Question image not found: {img_path}")
                b64_image = self._encode_image(img_path)
                mime_type = self._get_image_mime_type(img_path)
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64_image}", "detail": "high"}
                })

            # Add answer images
            for img_path in answer_image_paths:
                if not os.path.exists(img_path):
                    raise FileNotFoundError(f"Answer image not found: {img_path}")
                b64_image = self._encode_image(img_path)
                mime_type = self._get_image_mime_type(img_path)
                message_content.append({
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{b64_image}", "detail": "high"}
                })

            messages = [
                {"role": "system", "content": self.VISION_GRADING_PROMPT},
                {"role": "user", "content": message_content}
            ]

            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_completion_tokens=5000,
                response_format={"type": "json_object"}
            )

            log_llm_call(response, self.model_name, SERVICE_VISION_GRADING)
            
            result_json = json.loads(response.choices[0].message.content)
            return result_json

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            return {"is_correct": False, "confidence": 0.0, "error_description": "Failed to parse AI response", "error_phrases": [], "partial_credit": False}
        except Exception as e:
            logger.error(f"Async API request failed: {e}")
            return {"is_correct": False, "confidence": 0.0, "error_description": f"API error: {str(e)}", "error_phrases": [], "partial_credit": False}

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
                    answer_image_paths=item['answer_image_paths']
                )
        
        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks)
        
        logger.info(f"Async batch grading completed for {len(items)} items")
        return results