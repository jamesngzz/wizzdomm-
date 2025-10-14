## Migration Mirroring Spec (Old Streamlit → New Django/React)

This document recites, verbatim, the exact pieces of logic, prompts, data contracts, and UI behaviors from the old Streamlit codebase that MUST be mirrored in the new Django + React project.

### UI Behavior to Mirror (as Product Requirements)

- Left pane: scrollable canvas showing the student's submission images. Comments/annotations for a specific question must appear near that question’s region and on the correct page (e.g., “bài 2” comments appear around page 5 region).
- Right pane: detailed grading explanation synced to the currently viewed canvas page, including:
  - OCR doubts to confirm/fix (yellow tags), always at the top, max 10 cards.
  - Detailed explanation/errors corresponding to the currently visible submission page.
- Cropping workflow:
  1) Admin manually crops the target answer region on the correct submission page.
  2) Save cropping coordinates and original image dimensions.
  3) Insert comments/annotations at the saved coordinates.
- Regrade flow: teacher clarifies mistakes (due to OCR or handwriting), AI regrades using the clarification.
- Optional voice-to-text for LaTeX input to speed up entering math expressions.
- Export: produce a single merged PDF (all images in one file). Delivery via manual Zalo OA send.
- Admin capabilities: Crop images and check database state.

---

### Prompts (VERBATIM – must be used exactly)

#### GEMINI_VISION_GRADING_PROMPT (from `old/core/prompts.py`)

````
GEMINI_VISION_GRADING_PROMPT = """
Một giáo viên Toán Việt Nam tài giỏi 20 năm kinh nghiệm, sở trường của bạn là phân tích sâu sắc bài giải của học sinh và đưa ra nhận xét chính xác, công tâm.
**IMAGES INPUT:**
1.  **ẢNH ĐỀ BÀI:** Nội dung câu hỏi.
2.  **ẢNH BÀI LÀM:** Lời giải viết tay của học sinh.
3.  **LỜI GIẢI THAM KHẢO:** Các bước giải chuẩn để so sánh (nếu có).

### **TRIẾT LÝ VÀ QUY TRÌNH CHẤM BÀI**

**Bước 1: Đọc Hiểu Toàn Diện**
*   Đầu tiên, đọc kỹ **ẢNH ĐỀ BÀI** để nắm vững yêu cầu, điều kiện và mục tiêu bài toán.
*   Nếu có **LỜI GIẢI THAM KHẢO**, đọc kỹ để hiểu cách giải chuẩn và các bước logic chính.
*   Tiếp theo, đọc lướt toàn bộ **ẢNH BÀI LÀM**. Mục đích là hiểu tổng quan luồng tư duy và cấu trúc bài giải TRƯỚC KHI đi vào chi tiết.
*   Tạm thời ghi nhận những đoạn chữ viết tay không rõ ràng và chuẩn bị tinh thần để áp dụng kỹ thuật giải mã ngữ cảnh ở bước sau, **tuyệt đối không vội vàng phán xét hay gán lỗi.**

**Bước 2: Phân tích Logic và Giải Mã Ngữ Cảnh (Root Cause Analysis)**
Đây là bước quan trọng nhất. Dò theo từng bước lập luận của học sinh, kết hợp phân tích logic với kỹ năng giải mã chữ viết:

*   **2.1. So Sánh với Lời Giải Tham Khảo:**
    *   Nếu có lời giải tham khảo, so sánh từng bước của học sinh với các bước chuẩn.
    *   Học sinh có chọn đúng phương pháp, định lý, công thức để giải quyết vấn đề không?
    *   Tư duy tổng thể có đi đúng hướng để đạt được mục tiêu của bài toán không?

*   **2.2. Giải Mã Chữ Viết Không Rõ Ràng - CHỈ ĐỊNH VỊ TRÍ CỤ THỂ:**
    *   Khi gặp các ký tự, số liệu, hoặc biểu thức viết tay không rõ ràng, **PHẢI CHỈ ĐỊNH CHÍNH XÁC VỊ TRÍ** như: "dòng 3, cột 2", "phương trình thứ 2", "biểu thức cuối trang", "ký tự thứ 5 trong công thức".
    *   **TUYỆT ĐỐI không vội vàng đưa ra phán xét sai.** Thay vào đó, **tạm dừng và thực hiện phân tích ngữ cảnh sâu rộng:**
        *   **Logic Biến Đổi Trước và Sau:** Dựa vào các bước lập luận, phép tính, và biến đổi toán học *ngay trước và ngay sau* vị trí ký tự đó.
        *   **Ưu tiên Ý Định Đúng (Principle of Charity):** Ưu tiên cách đọc nào giúp cho lập luận của học sinh có *khả năng đúng* hoặc *ít sai sót hơn* trong bối cảnh chung của bài giải.

*   **2.3. Phân Tích Đặc Biệt cho BÀI CHỨNG MINH:**
    *   **QUAN TRỌNG:** Với các bài toán chứng minh, không có đáp án số cụ thể, mục đích cuối cùng là chứng minh mệnh đề đúng.
    *   **CHẤM CHẶT HỎI LOGIC:** Nếu học sinh kết luận đúng mệnh đề chứng minh nhưng logic hoàn toàn không liên quan hoặc có lỗi nghiêm trọng, phải chấm SAI hoàn toàn.
    *   **VÍ DỤ SAI:** Chứng minh "tam giác ABC cân" nhưng lập luận dựa trên diện tích hình tròn → SAI HOÀN TOÀN dù kết luận đúng.

*   **2.4. Phân Tích Phần Gạch Xóa:**
    *   **Bước đầu tiên:** Xác định TẤT CẢ các phần có dấu hiệu gạch xóa (đường kẻ ngang, zigzag, tô đen, v.v.). ĐÔI KHI học sinh gạch xóa một vài kí tự nhỏ (toán tử) nên khó xác định nên phải nhìn kĩ để hiểu ý định học sinh.
    *   **PHÂN LOẠI GẠCH XÓA - THEN CHỐT:**
        *   **LOẠI 1 - GẠCH XÓA DO SAI/SỬA ĐỔI:** Học sinh viết sai rồi gạch để sửa lại → **HOÀN TOÀN BỎ QUA**
        *   **LOẠI 2 - GẠCH XÓA DO TRIỆT TIÊU TOÁN HỌC:** Học sinh cố ý gạch để triệt tiêu các số hạng đối nhau → **PHẢI TÍNH VÀO**

*   **2.5. Tìm "Lỗi Gốc" (Root Cause Analysis):**
        *   Nếu có nhiều lỗi sai, tập trung vào *lỗi sai đầu tiên và cơ bản nhất* đã gây ra chuỗi sai lầm sau đó. Ví dụ, nếu học sinh tính sai biệt thức Delta ngay từ đầu, dẫn đến toàn bộ phần tìm nghiệm phía sau đều sai, thì "lỗi gốc" là "Tính sai biệt thức Delta". 
        Tôi sẽ chỉ ra lỗi gốc này để học sinh hiểu vấn đề cốt lõi cần khắc phục.

### **TIÊU CHÍ ĐÁNH GIÁ**
✅ ĐÚNG: Khi **phương pháp + đáp án** đều đúng. Lời giải hợp lý về mặt toán học, không chứa lỗi logic nghiêm trọng. **Đôi khi học sinh làm đúng phương pháp nhưng có một vài thay đổi nhỏ, không ảnh hưởng đến logic thì chấp nhận nó, không làm sao cả.**
🔄 ĐIỂM MỘT PHẦN: Phương pháp đúng hoặc đáp án đúng nhưng sai sót nhỏ trong tính toán, hoặc các lỗi không đáng kể.
❌ SAI: Phương pháp sai hoặc đáp án sai hoặc đúng một cách "may mắn" nhưng có lỗ hổng logic nghiệm trọng.
❌ KHÔNG LÀM BÀI: Bỏ trống hoặc bài làm không đọc được.

### **YÊU CẦU OUTPUT (BẮT BUỘC)**

Bạn phải trả về một đối tượng JSON duy nhất với cấu trúc chính xác như sau:

```json
{
  "is_correct": true/false,
  "critical_errors": [
    {
      "description": "Mô tả lỗi nghiêm trọng ảnh hưởng đến logic chính",
      "phrases": ["Phrase cụ thể và chi tiết chỉ rõ lỗi"] # 1 phrase  VD: "Chuyển vế đổi dấu sai: 2 + x = 5 => x = 5 + 2"
    }
  ], #Lỗi sai chí mạng làm ảnh hưởng nhiều đến mạch logic làm bài.
  "part_errors": [
    {
      "description": "Mô tả lỗi nhỏ hoặc không chắc chắn do OCR",
      "phrases": ["Phrase cụ thể và chi tiết chỉ rõ lỗi"] # 1 phrase VD: "Viết nhầm tên công thức Pythargore sang Bitagore"
    }
  ], #Lỗi nhỏ, không đáng kể hoặc không chắc chắn do chữ viết không rõ ràng. VD: Sai tính toán nhỏ, viết mơ hồ
  "partial_credit": true/false # Trong quá trình làm bài tồn tại những bước đúng
}

**CHỈ DẪN PHÂN LOẠI LỖI:**
- **CRITICAL_ERRORS:** Lỗi làm sai lệch hoàn toàn logic bài làm, ảnh hưởng đến kết quả cuối
- **PART_ERRORS:** Lỗi nhỏ, không ảnh hưởng logic chính, hoặc do không chắc chắn khi đọc chữ viết
- Nếu không có lỗi nào trong loại đó thì để array rỗng []
- Mỗi error có description (chi tiết) và phrases (ngắn gọn để hiển thị)
"""
````

#### OPENAI_MATH_SOLVING_PROMPT (from `old/core/prompts.py`)

````
OPENAI_MATH_SOLVING_PROMPT = """
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
````

---

### Data Models (VERBATIM FIELDS to mirror semantics)

From `old/database/models_v2.py` – field contracts to mirror:

```python
class ExamV2(Base):
    __tablename__ = "v2_exams"
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    topic = Column(String(100), nullable=False)
    grade_level = Column(String(16), nullable=False)
    original_image_paths = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime_now_seconds)

class QuestionV2(Base):
    __tablename__ = "v2_questions"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("v2_exams.id"), nullable=False)
    question_image_path = Column(String(512), nullable=False)
    question_image_paths = Column(String, nullable=True)
    has_multiple_images = Column(Boolean, default=False)
    order_index = Column(Integer, nullable=False)
    part_label = Column(String(32))
    solution_answer = Column(String, nullable=True)
    solution_steps = Column(String, nullable=True)
    solution_points = Column(String, nullable=True)
    solution_verified = Column(Boolean, default=False)
    solution_generated_at = Column(DateTime, nullable=True)

class SubmissionV2(Base):
    __tablename__ = "v2_submissions"
    id = Column(Integer, primary_key=True)
    exam_id = Column(Integer, ForeignKey("v2_exams.id"), nullable=False)
    student_name = Column(String(255), nullable=False)
    original_image_paths = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime_now_seconds)

class SubmissionItemV2(Base):
    __tablename__ = "v2_submission_items"
    id = Column(Integer, primary_key=True)
    submission_id = Column(Integer, ForeignKey("v2_submissions.id"), nullable=False)
    question_id = Column(Integer, ForeignKey("v2_questions.id"), nullable=False)

    # Can store either single integer (backward compatibility) or JSON array for multi-page answers
    source_page_index = Column(String, nullable=False, default='0')

    answer_image_path = Column(String(512), nullable=False)
    answer_image_paths = Column(String, nullable=True)
    has_multiple_images = Column(Boolean, default=False)

    # Bounding box coordinates for precise canvas positioning
    answer_bbox_coordinates = Column(String, nullable=True)  # {left, top, width, height}
    original_image_dimensions = Column(String, nullable=True)  # {width, height}

class GradingV2(Base):
    __tablename__ = "v2_gradings"
    id = Column(Integer, primary_key=True)
    submission_item_id = Column(Integer, ForeignKey("v2_submission_items.id"), nullable=False, unique=True)
    question_id = Column(Integer, ForeignKey("v2_questions.id"), nullable=False)
    is_correct = Column(Boolean, nullable=False)
    error_description = Column(String, nullable=True)  # Legacy field
    error_phrases = Column(String, nullable=True)      # Legacy field
    critical_errors = Column(String, nullable=True)    # JSON array
    part_errors = Column(String, nullable=True)        # JSON array
    partial_credit = Column(Boolean, default=False)
    teacher_notes = Column(String, nullable=True)
    clarify_notes = Column(String, nullable=True)
    graded_at = Column(DateTime, default=datetime_now_seconds)
```

Helper semantics for page indices (must mirror): from `old/database/manager_v2.py`:

```python
@staticmethod
def encode_source_page_indices(indices: Union[int, List[int]]) -> str:
    if isinstance(indices, int):
        return str(indices)
    elif isinstance(indices, list):
        return json.dumps(indices)
    else:
        return '0'

@staticmethod
def decode_source_page_indices(indices_str: str) -> List[int]:
    try:
        if indices_str.startswith('['):
            return json.loads(indices_str)
        else:
            return [int(indices_str)]
    except (json.JSONDecodeError, ValueError):
        return [0]
```

---

### Grading Flow (VERBATIM semantics)

From `old/services/grading_service.py` – core mapping to DB and legacy compatibility:

```python
ai_result = self.ai_model.grade_image_pair(
    question_paths, answer_paths,
    clarify=clarify, previous_grading=previous_grading, solution=solution
)

# Handle both new and legacy error formats
critical_errors = ai_result.get('critical_errors', [])
part_errors = ai_result.get('part_errors', [])

# Legacy support: if old format is present, convert to new format
if ai_result.get('error_description') and not critical_errors and not part_errors:
    legacy_error = {
        "description": ai_result.get('error_description', ''),
        "phrases": ai_result.get('error_phrases', [])
    }
    critical_errors = [legacy_error] if legacy_error["description"] else []

grading_id = db_manager.create_grading(
    submission_item_id=item.id,
    question_id=question.id,
    is_correct=ai_result.get('is_correct', False),
    error_description=ai_result.get('error_description'),  # keep legacy
    error_phrases=ai_result.get('error_phrases', []),      # keep legacy
    critical_errors=critical_errors,
    part_errors=part_errors,
    partial_credit=ai_result.get('partial_credit', False),
    clarify_notes=clarify
)
```

Batch grading mirrors the same conversion for each item.

---

### Canvas Anchoring Logic (VERBATIM behavior)

From `old/components/canvas_helper.py`:

```python
@staticmethod
def _scale_bbox_to_canvas(bbox_coords: Dict, original_dims: Dict, canvas_width: int) -> Dict:
    if not bbox_coords or not original_dims:
        return None
    try:
        scale_factor = canvas_width / original_dims['width']
        return {
            'left': int(bbox_coords['left'] * scale_factor),
            'top': int(bbox_coords['top'] * scale_factor),
            'width': int(bbox_coords['width'] * scale_factor),
            'height': int(bbox_coords['height'] * scale_factor)
        }
    except (KeyError, TypeError, ZeroDivisionError):
        return None
```

Per-page filtering and placement (must replicate the same semantics):

```python
# Filter items for current page (supports multi-page items)
items_for_this_page = []
for item in graded_items:
    source_page_indices = item.get('source_page_indices', [item.get('source_page_index', 0)])
    if current_page_index in source_page_indices:
        items_for_this_page.append(item)

# Positioning: use scaled bbox if available, else stack on the left margin
if scaled_bbox:
    phrase_left = scaled_bbox['left']
    phrase_top = scaled_bbox['top']
else:
    phrase_left = 10
    phrase_top = current_top
    current_top += 60

# Render types:
# - ✅ when is_correct
# - ❌ for critical_errors phrases
# - ⚠️ for part_errors phrases
# If no new-format errors present, fallback to legacy error_phrases
```

---

### Config Values to Mirror

From `old/core/config.py`:

```python
SUPPORTED_IMAGE_FORMATS = ["png", "jpg", "jpeg"]
SUPPORTED_FILE_FORMATS = ["png", "jpg", "jpeg", "pdf"]
MAX_IMAGE_SIZE_MB = 50
MAX_PDF_SIZE_MB = 20  # Gemini limit for inline PDF

CROP_BOX_COLOR = "#0066CC"  # Blue color for crop box
CROP_REALTIME_UPDATE = True
```

These constraints should be preserved in both backend file validation and frontend uploader/cropper UX.

---

### Solution Generation Semantics (Optional but keep structure)

From `old/services/question_solver_service.py` – fields updated when generating solutions:

```python
success = db_manager.update_question_solution(
    question_id=question_id,
    solution_answer=solution.get('answer', ''),
    solution_steps=json.dumps(solution.get('steps', []), ensure_ascii=False),
    solution_points=json.dumps([step.get('points', 0) for step in solution.get('steps', [])], ensure_ascii=False),
    solution_verified=False,  # Requires teacher approval
    solution_generated_at=datetime.now()
)
```

Mirror these fields and the verification toggle if/when solver is ported.

---

### Export & Delivery

- Export must produce a single merged PDF containing either all original submission pages or all cropped answers, in order, for simple download.
- Delivery via manual Zalo OA send (no integration required at this stage); ensure the exported file path/URL is easily accessible.

---

### Acceptance Checklist

- Prompts match EXACT content above.
- Grading JSON schema identical; legacy compatibility maintained.
- Data fields and semantics preserved (multi-images, page indices, bbox + original dimensions).
- Canvas positioning uses width-based scaling; fallback stacking on left.
- Right pane shows OCR doubts (max 10) first, then detailed explanation synced to current page.
- Regrade with teacher clarification updates same grading row.
- Export merges into one PDF and is downloadable for manual Zalo send.





