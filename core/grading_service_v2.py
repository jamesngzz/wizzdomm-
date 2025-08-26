import os
import json
import base64
import logging
from typing import Dict, Any, Optional, List, Tuple
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from .llm_logger import log_llm_call, log_batch_summary, SERVICE_VISION_GRADING, SERVICE_BATCH_GRADING

# Load environment variables
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

@dataclass
class GradingResult:
    """Data class for grading results"""
    question_id: int
    submission_item_id: int
    is_correct: bool
    confidence: float
    error_description: str
    error_phrases: List[str] = None
    partial_credit: bool = False
    processing_time: float = 0.0
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.error_phrases is None:
            self.error_phrases = []

class VisionGradingService:
    
    # Enhanced grading prompt optimized through testing
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
```
### **VÍ DỤ MINH HỌA**

{
  "is_correct": false,
  "confidence": 0.96,
  "error_description": "Học sinh đã áp dụng đúng các bước giải phương trình bậc nhất, bao gồm khai triển, thu gọn và chuyển vế. Tuy nhiên, có một lỗi nhỏ trong bước tính toán cuối cùng khi chuyển hạng tử tự do từ vế trái sang vế phải: thay vì (-1) + 1 = 0, học sinh đã viết (-1) - 1 = -2, dẫn đến đáp án sai. Lỗi này là một sai sót về kỹ năng tính toán/chuyển dấu, không phải lỗi về phương pháp tư duy tổng thể.",
  "error_phrases":["Lỗi tính toán khi chuyển hạng tử tự do"]
  "partial_credit": true
}

"""

    def __init__(self, api_key: Optional[str] = None):
        """Initialize the grading service"""
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable.")
        
        self.client = OpenAI(api_key=self.api_key)
        self.model_name = "gpt-5-mini"
        
        logger.info(f"VisionGradingService initialized with model: {self.model_name}")
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64"""
        try:
            with open(image_path, "rb") as image_file:
                return base64.b64encode(image_file.read()).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to encode image {image_path}: {e}")
            raise
    
    def _get_image_mime_type(self, image_path: str) -> str:
        """Determine MIME type from file extension"""
        ext = Path(image_path).suffix.lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.webp': 'image/webp'
        }
        return mime_map.get(ext, 'image/jpeg')
    
    def grade_image_pair(self, question_image_path: str, answer_image_path: str, 
                        question_image_paths: List[str] = None, answer_image_paths: List[str] = None) -> Dict[str, Any]:
        """
        Grade a student's answer by analyzing question and answer images
        
        Args:
            question_image_path: Path to the question image
            answer_image_path: Path to the student's answer image
            question_image_paths: List of paths for multi-image questions
            answer_image_paths: List of paths for multi-image answers
            
        Returns:
            Dictionary containing grading results
        """
        start_time = datetime.now()
        
        logger.info(f"Grading image pair: {Path(question_image_path).name} vs {Path(answer_image_path).name}")
        
        try:
            # Validate files exist
            if not os.path.exists(question_image_path):
                raise FileNotFoundError(f"Question image not found: {question_image_path}")
            if not os.path.exists(answer_image_path):
                raise FileNotFoundError(f"Answer image not found: {answer_image_path}")
            
            # Validate additional answer images if provided
            if answer_image_paths:
                for img_path in answer_image_paths:
                    if not os.path.exists(img_path):
                        logger.warning(f"Answer image not found: {img_path}")
            
            # Prepare message content
            message_content = [
                {
                    "type": "text",
                    "text": "Hãy chấm bài tự luận toán của học sinh. Bạn sẽ nhận đầu vào hình ảnh bao gồm NHỮNG HÌNH ẢNH ĐỀ BÀI & HÌNH ẢNH BÀI LÀM HỌC SINH"
                }
            ]
            
            # Add question image(s)
            if question_image_paths and len(question_image_paths) > 1:
                # Multiple question images
                for i, img_path in enumerate(question_image_paths, 1):
                    if os.path.exists(img_path):
                        question_b64 = self._encode_image(img_path)
                        question_mime = self._get_image_mime_type(img_path)
                        message_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{question_mime};base64,{question_b64}",
                                "detail": "high"
                            }
                        })
            else:
                # Single question image (backward compatibility)
                question_b64 = self._encode_image(question_image_path)
                question_mime = self._get_image_mime_type(question_image_path)
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{question_mime};base64,{question_b64}",
                        "detail": "high"
                    }
                })
            
            # Add answer image(s)
            if answer_image_paths and len(answer_image_paths) > 1:
                # Multiple answer images
                for i, img_path in enumerate(answer_image_paths, 1):
                    if os.path.exists(img_path):
                        answer_b64 = self._encode_image(img_path)
                        answer_mime = self._get_image_mime_type(img_path)
                        message_content.append({
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{answer_mime};base64,{answer_b64}",
                                "detail": "high"
                            }
                        })
            else:
                # Single answer image (backward compatibility)
                answer_b64 = self._encode_image(answer_image_path)
                answer_mime = self._get_image_mime_type(answer_image_path)
                message_content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{answer_mime};base64,{answer_b64}",
                        "detail": "high"
                    }
                })
            
            # Prepare API messages
            messages = [
                {
                    "role": "system",
                    "content": self.VISION_GRADING_PROMPT
                },
                {
                    "role": "user",
                    "content": message_content
                }
            ]
            
            # Call OpenAI API
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                max_completion_tokens=4000,
                response_format={"type": "json_object"}
            )
            
            # Log LLM usage
            log_llm_call(response, self.model_name, SERVICE_VISION_GRADING)
            
            # Parse response
            result_json = json.loads(response.choices[0].message.content)
            
            # Add metadata
            processing_time = (datetime.now() - start_time).total_seconds()
            result_json.update({
                "processing_time": processing_time
            })
            
            logger.info(f"Grading completed in {processing_time:.2f}s - Result: {result_json['is_correct']}")
            
            return result_json
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed: {e}")
            return self._error_result(f"AI response parsing failed: {e}")
            
        except Exception as e:
            logger.error(f"Grading failed: {e}")
            return self._error_result(f"Grading error: {e}")
    
    def _error_result(self, error_msg: str) -> Dict[str, Any]:
        """Return standardized error result"""
        return {
            "is_correct": False,
            "confidence": 0.0,
            "error_description": error_msg,
            "partial_credit": False,
            "processing_time": 0.0,
            "error": True
        }
    
    def grade_submission_items(self, submission_items: List[Dict]) -> List[GradingResult]:
        """
        Grade multiple submission items
        
        Args:
            submission_items: List of dicts with question_image_path, answer_image_path, etc.
            
        Returns:
            List of GradingResult objects
        """
        results = []
        batch_start_time = datetime.now()
        total_cost = 0.0
        
        logger.info(f"Grading batch of {len(submission_items)} items")
        
        for i, item in enumerate(submission_items, 1):
            logger.info(f"Processing item {i}/{len(submission_items)}")
            
            try:
                grading_result = self.grade_image_pair(
                    item['question_image_path'],
                    item['answer_image_path'],
                    question_image_paths=item.get('question_image_paths'),
                    answer_image_paths=item.get('answer_image_paths')
                )
                
                result = GradingResult(
                    question_id=item.get('question_id', 0),
                    submission_item_id=item.get('submission_item_id', 0),
                    is_correct=grading_result['is_correct'],
                    confidence=grading_result.get('confidence', 0.0),
                    error_description=grading_result['error_description'],
                    error_phrases=grading_result.get('error_phrases', []),
                    partial_credit=grading_result.get('partial_credit', False),
                    processing_time=grading_result.get('processing_time', 0.0)
                )
                
                results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to grade item {i}: {e}")
                # Create error result
                error_result = GradingResult(
                    question_id=item.get('question_id', 0),
                    submission_item_id=item.get('submission_item_id', 0),
                    is_correct=False,
                    confidence=0.0,
                    error_description=f"Grading failed: {str(e)}",
                    error_phrases=[],
                    partial_credit=False
                )
                results.append(error_result)
        
        # Calculate batch processing time and log summary
        batch_time = (datetime.now() - batch_start_time).total_seconds()
        
        # Note: Actual cost calculation is done in individual calls via log_llm_call
        # This is just a summary log
        log_batch_summary(len(submission_items), 0.0, SERVICE_BATCH_GRADING)
        
        logger.info(f"Batch grading completed: {len(results)} results generated in {batch_time:.2f}s")
        return results


# Global service instance
_grading_service = None

def get_grading_service() -> VisionGradingService:
    """Get global grading service instance"""
    global _grading_service
    if _grading_service is None:
        _grading_service = VisionGradingService()
    return _grading_service

# Convenience functions
def grade_single_pair(question_image_path: str, answer_image_path: str) -> Dict[str, Any]:
    """Grade a single question-answer pair"""
    service = get_grading_service()
    return service.grade_image_pair(question_image_path, answer_image_path)

def grade_multiple_pairs(submission_items: List[Dict]) -> List[GradingResult]:
    """Grade multiple question-answer pairs"""
    service = get_grading_service()
    return service.grade_submission_items(submission_items)