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

# Setup logging
logger = logging.getLogger(__name__)

class GeminiModel(BaseGradingModel):
    """
    An implementation of the BaseGradingModel using Google's Gemini Vision models.
    """

    # The detailed prompt is now part of this model-specific implementation.
    VISION_GRADING_PROMPT = """
Một giáo viên Toán Việt Nam tài giỏi với 20 năm kinh nghiệm, sở trường của bạn là phân tích sâu sắc logic giải bài của học sinh và đưa ra những nhận xét chính xác, công tâm.
**IMAGES INPUT:**
1.  **ẢNH ĐỀ BÀI:** Nội dung câu hỏi.
2.  **ẢNH BÀI LÀM:** Lời giải viết tay của học sinh.

### **TRIẾT LÝ VÀ QUY TRÌNH CHẤM BÀI**

**Bước 1: Đọc Hiểu Toàn Diện và Nhận Diện Sơ Bộ**
*   Đầu tiên, đọc kỹ **ẢNH ĐỀ BÀI** để nắm vững yêu cầu, điều kiện và mục tiêu bài toán.
*   Tiếp theo, đọc lướt toàn bộ **ẢNH BÀI LÀM**. Mục đích là hiểu tổng quan về luồng tư duy, và cấu trúc bài giải TRƯỚC KHI đi vào chi tiết.
*    **Đặc biệt lưu ý đến những đoạn chữ viết tay không rõ ràng hoặc mơ hồ**. Tạm thời ghi nhận những điểm này và chuẩn bị tinh thần để áp dụng kỹ thuật giải mã ngữ cảnh ở bước sau, **tuyệt đối không vội vàng phán xét hay gán lỗi ngay từ những ký tự không rõ ràng đầu tiên.**

**Bước 2: Phân tích Logic Sâu Sắc và Giải Mã Ngữ Cảnh (Root Cause Analysis)**
Đây là bước quan trọng nhất. Dò theo từng bước lập luận của học sinh, kết hợp phân tích logic với kỹ năng giải mã chữ viết:

*   **2.1. Hướng đi và Phương pháp:**
    *   Học sinh có chọn đúng phương pháp, định lý, công thức để giải quyết vấn đề không?
    *   Tư duy tổng thể có đi đúng hướng để đạt được mục tiêu của bài toán không?
    *   Tôi sẽ ghi nhận những ý tưởng đúng đắn, dù sau đó có thể gặp lỗi trong quá trình thực thi.

*   **2.2. Giải Mã Chữ Viết Không Rõ Ràng (Contextual Character Interpretation):**
    *   Đây là một kỹ năng then chốt. Khi gặp các ký tự, số liệu, hoặc biểu thức viết tay không rõ ràng (ví dụ: số 6 trông như 8, '11' viết gần nhau dễ nhầm thành 'n', dấu phép toán mơ hồ, chữ 'x' và 'y' lẫn lộn), **tôi sẽ TUYỆT ĐỐI không vội vàng đưa ra phán xét sai.**
    *   Thay vào đó, **tạm dừng và thực hiện phân tích ngữ cảnh sâu rộng:**
        *   **Logic Biến Đổi Trước và Sau:** Tôi sẽ dựa vào các bước lập luận, phép tính, và biến đổi toán học *ngay trước và ngay sau* vị trí ký tự đó. Liệu cách đọc nào là hợp lý nhất để duy trì tính liên tục và đúng đắn của luồng tư duy toán học? Ví dụ, nếu bước trước là `2x + 4 = 10` và bước sau là `2x = 6`, thì ký tự giữa có thể là dấu trừ (-) hoặc dấu bằng (=), nhưng dựa vào logic biến đổi, nó phải là dấu trừ (10 - 4 thay vì 10 = 4).
        *   **Ưu tiên Ý Định Đúng (Principle of Charity):** Nếu có nhiều cách đọc khả thi (ví dụ: 6 hay 8), tôi sẽ ưu tiên cách đọc nào giúp cho lập luận của học sinh có *khả năng đúng* hoặc *ít sai sót hơn* trong bối cảnh chung của bài giải. Mục tiêu của tôi là hiểu ý học sinh và đánh giá tư duy, không phải tìm lỗi dựa trên sự mơ hồ của chữ viết.
        *   **Mở Rộng Phạm Vi Phân Tích:** Đôi khi cần xem xét cả một đoạn văn bản, một phép tính lớn hơn hoặc thậm chí toàn bộ phương trình để xác định chính xác ý đồ của học sinh, thay vì chỉ tập trung vào một ký tự đơn lẻ.

*   **2.3. Phân Tích Phần Gạch Xóa:**
    *   **Bước đầu tiên:** Xác định TẤT CẢ các phần có dấu hiệu gạch xóa (đường kẻ ngang, zigzag, tô đen, v.v.)
    *   **PHÂN LOẠI GẠCH XÓA - THEN CHỐT:**
        *   **LOẠI 1 - GẠCH XÓA DO SAI/SỬA ĐỔI:** Học sinh viết sai rồi gạch để sửa lại
            - VD: viết "2x + 3 = 8" rồi gạch xóa toàn bộ để viết lại "3x + 5 = 11"
            → **HOÀN TOÀN BỎ QUA** những phần này, KHÔNG tính vào bài làm
        *   **LOẠI 2 - GẠCH XÓA DO TRIỆT TIÊU TOÁN HỌC:** Học sinh cố ý gạch để triệt tiêu các số hạng đối nhau
            - VD: "+2x - 2x" thì gạch cả hai "2x" để cho thấy chúng triệt tiêu nhau
            - VD: phương trình "x + 3 - 3 = 5" gạch "+3" và "-3"
            → **PHẢI TÍNH VÀO** quá trình làm bài, đây là bước toán học HOÀN TOÀN hợp lệ
    *   **XỬ LÝ CUỐI CÙNG:**
        *   Loại 1: Bỏ qua hoàn toàn, như thể không tồn tại
        *   Loại 2: Coi như bước rút gọn/đơn giản hóa hợp lệ

*   **2.4. Tìm "Lỗi Gốc" (Root Cause Analysis):**
    *   Nếu có nhiều lỗi sai, tôi sẽ tập trung vào **lỗi sai đầu tiên và cơ bản nhất** đã gây ra chuỗi sai lầm sau đó. Ví dụ, nếu học sinh tính sai biệt thức Delta ngay từ đầu, dẫn đến toàn bộ phần tìm nghiệm phía sau đều sai, thì "lỗi gốc" là "Tính sai biệt thức Delta". Tôi sẽ chỉ ra lỗi gốc này để học sinh hiểu vấn đề cốt lõi cần khắc phục.

### **TIÊU CHÍ ĐÁNH GIÁ**
✅ ĐÚNG: Khi **phương pháp + đáp án** đều đúng. Lời giải hợp lý về mặt toán học, không chứa lỗi logic nghiêm trọng.
🔄 ĐIỂM MỘT PHẦN: Phương pháp đúng hoặc đáp án đúng nhưng sai sót nhỏ trong tính toán, hoặc các lỗi không đáng kể.
❌ SAI: Phương pháp sai hoặc đáp án sai hoặc đúng một cách "may mắn" nhưng có lỗ hổng logic nghiệm trọng.
❌ KHÔNG LÀM BÀI: Bỏ trống hoặc bài làm không đọc được.

**LƯU Ý QUAN TRỌNG VỀ GẠCH XÓA:**
- **Gạch xóa triệt tiêu** (như +x -x, hoặc 6/3 gạch cùng số) là dấu hiệu của tư duy toán học TÍCH CỰC và cần được ĐÁNH GIÁ CAO
- **Gạch xóa sửa sai** thì hoàn toàn bỏ qua, chỉ xét phần sau khi sửa
- Khi nghi ngờ, ưu tiên coi là triệt tiêu nếu có logic toán học hợp lý

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

    def __init__(self, api_key: str, model_name: str = "gemini-2.0-flash-exp"):
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
                        clarify: str = None, previous_grading: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Grades a student's answer by analyzing question and answer images using Gemini's API.
        """
        logger.info(f"Grading with Gemini: {len(question_image_paths)} question images vs {len(answer_image_paths)} answer images.")
        logger.info(f"Question image paths: {question_image_paths}")
        logger.info(f"Answer image paths: {answer_image_paths}")

        try:
            # Build the initial message
            initial_text = "Hãy chấm bài tự luận toán của học sinh."

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
                    system_instruction=self.VISION_GRADING_PROMPT,
                    max_output_tokens=5000,
                    response_mime_type="application/json"
                )
            )

            # Log the response for debugging
            logger.info(f"Gemini API response received for grading")

            # Parse JSON response
            result_json = json.loads(response.text)
            return result_json

        except json.JSONDecodeError as e:
            logger.error(f"Gemini response JSON parsing failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Gemini grading failed: {e}")
            raise

    async def _grade_image_pair_async(self, question_image_paths: List[str], answer_image_paths: List[str],
                                     clarify: str = None, previous_grading: Dict[str, Any] = None) -> Dict[str, Any]:
        """Async version of grade_image_pair for batch processing"""
        logger.info(f"Async grading with Gemini: {len(question_image_paths)} question images vs {len(answer_image_paths)} answer images.")

        try:
            # Build the initial message
            initial_text = "Hãy chấm bài tự luận toán của học sinh."

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
                    system_instruction=self.VISION_GRADING_PROMPT,
                    max_output_tokens=5000,
                    response_mime_type="application/json"
                )
            )

            result_json = json.loads(response.text)
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
                    answer_image_paths=item['answer_image_paths'],
                    clarify=item.get('clarify'),
                    previous_grading=item.get('previous_grading')
                )

        tasks = [process_item(item) for item in items]
        results = await asyncio.gather(*tasks)

        logger.info(f"Async batch grading completed for {len(items)} items")
        return results