# pages/grading_results_page.py
import streamlit as st
import os
import sys
import time
import json
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.state_manager import app_state
from services.submission_service import SubmissionService
from services.grading_service import grading_service
from services.results_service import results_service
from services.question_service import QuestionService
from components.shared_components import render_selection_box
from components.canvas_helper import CanvasHelper
from core.utils import format_question_label

def show_grading_results_page():
    """Trang tích hợp chấm bài và kết quả với regrade enhancement."""
    st.header("🎯 Chấm bài & Kết quả")
    st.markdown("Xem kết quả chấm bài AI và thực hiện chấm lại từng câu với clarification.")

    # Get submissions with answers
    success, _, submissions_data = SubmissionService.get_all_submissions_with_answers()

    if not submissions_data:
        st.warning("⚠️ Không tìm thấy bài làm học sinh nào có câu trả lời đã ánh xạ.")
        if st.button("➕ Chuyển đến trang bài làm"):
            app_state.page = "👥 Bài làm học sinh"
            st.rerun()
        return

    # Render unified header with selection and summary
    selected_data, graded_count, total_count, correct_count = render_unified_header(
        submissions_data, app_state.selected_submission_for_grading
    )

    if not selected_data:
        return

    # Clear the pre-selection after using it
    if app_state.selected_submission_for_grading:
        app_state.selected_submission_for_grading = None

    submission = selected_data['submission']
    items = selected_data['items']

    # Get grading data (moved inside unified header for efficiency)
    from database.manager_v2 import db_manager
    existing_gradings = {g.submission_item_id: g for g in db_manager.get_gradings_by_submission(submission.id)}

    # Only show detailed results if there are gradings
    if graded_count > 0:
        st.divider()

        # Get results data for visual feedback
        results_data = results_service.get_results_for_submission(submission.id)

        if results_data:
            # Two-column layout: Canvas (65%) | Question Cards (35%)
            col_canvas, col_cards = st.columns([0.65, 0.35])

            with col_canvas:
                # Visual Feedback Canvas (from results_page.py)
                current_page_index = render_visual_feedback_canvas(results_data, submission.id)

            with col_cards:
                # Enhanced Question Cards with Regrade - now filtered by current page
                render_enhanced_question_cards(items, existing_gradings, current_page_index)
        else:
            st.error("Không thể tải dữ liệu kết quả.")
    else:
        st.info("Bài làm này chưa được chấm điểm.")

        # Add grading functionality for ungraded submissions
        st.subheader("🚀 Bắt đầu chấm điểm")

        col1, col2 = st.columns([1, 1])

        with col1:
            if st.button("🤖 Chấm tự động toàn bộ", type="primary"):
                handle_grade_all_questions(submission.id, items)

        with col2:
            if st.button("📝 Chấm từng câu"):
                render_individual_grading_interface(items, {})

def render_unified_header(submissions_data, default_submission_id):
    """Render unified header combining selection and summary."""
    st.subheader("🎯 Chọn bài làm và tóm tắt kết quả")

    if not submissions_data:
        st.warning("⚠️ Không tìm thấy bài làm học sinh nào có câu trả lời đã ánh xạ.")
        return None, 0, 0, 0

    # Find default index if pre-selected submission exists
    default_index = 0
    if default_submission_id:
        for i, data in enumerate(submissions_data):
            if data['submission'].id == default_submission_id:
                default_index = i
                break

    # Create unified layout: Selection + Student + Exam + Questions + Accuracy
    col1, col2, col3, col4, col5 = st.columns([2.5, 1.2, 1.2, 0.8, 1.3])

    with col1:
        selected_index = st.selectbox(
            label="Chọn bài làm:",
            options=range(len(submissions_data)),
            format_func=lambda i: (
                f"{submissions_data[i]['submission'].student_name} - "
                f"{submissions_data[i].get('exam_name', 'N/A')}"
            ),
            index=default_index,
            key="unified_grading_selector"
        )

    selected_data = submissions_data[selected_index] if selected_index is not None else None

    if not selected_data:
        return None, 0, 0, 0

    # Get grading data to calculate stats
    from database.manager_v2 import db_manager
    gradings = db_manager.get_gradings_by_submission(selected_data['submission'].id)
    existing_gradings = {g.submission_item_id: g for g in gradings}

    graded_count = len(existing_gradings)
    total_count = len(selected_data['items'])
    correct_count = sum(1 for g in existing_gradings.values() if g.is_correct)

    # Display metrics in remaining columns
    with col2:
        st.metric("👤 Học sinh", selected_data['submission'].student_name)

    with col3:
        exam_name = selected_data.get('exam_name', 'N/A')
        st.metric("📝 Đề thi", exam_name)

    with col4:
        st.metric("❓ Câu hỏi", f"{total_count}")

    with col5:
        if graded_count > 0:
            accuracy = (correct_count / graded_count) * 100
            st.metric(
                "🎯 Độ chính xác",
                f"{accuracy:.1f}%",
                help=f"{correct_count}/{graded_count} câu đúng"
            )
        else:
            st.metric("📊 Tiến độ", f"0/{total_count}")

    return selected_data, graded_count, total_count, correct_count

def render_visual_feedback_canvas(results_data, submission_id):
    """Render visual feedback canvas from results_page.py."""
    st.subheader("✍️ Canvas phản hồi trực quan")

    image_paths = results_data['submission_image_paths']

    if not image_paths:
        st.warning("Không tìm thấy hình ảnh bài làm cho bài nộp này.")
        return 0  # Return default page index

    # Page selection for multi-page submissions
    page_index = 0
    if len(image_paths) > 1:
        page_selection = st.selectbox(
            "Chọn trang để chú thích:",
            options=[f"Trang {i+1}" for i in range(len(image_paths))],
            key=f"page_select_{submission_id}"
        )
        page_index = int(page_selection.split(" ")[1]) - 1

    try:
        bg_image = Image.open(image_paths[page_index]).convert("RGBA")
    except FileNotFoundError:
        st.error(f"Không tìm thấy hình ảnh tại đường dẫn: {image_paths[page_index]}")
        return

    # Scale image for display - calculate dimensions before generating initial drawing
    max_width = 700  # Reasonable size for the canvas column
    scale_factor = min(max_width / bg_image.width, 1.0)
    display_width = int(bg_image.width * scale_factor)
    display_height = int(bg_image.height * scale_factor)

    # Circle count control
    circle_count = st.slider("Số hình tròn cần thêm:", min_value=0, max_value=15, value=0, step=1)

    initial_drawing = CanvasHelper.generate_initial_drawing(
        graded_items=results_data['graded_items'],
        current_page_index=page_index,
        circle_count=circle_count,
        image_width=display_width
    )

    st.info("💡 **Hướng dẫn:** Kéo thả để di chuyển phrase. Chuột phải vào phrase → chọn Delete để xóa.")

    canvas_result = st_canvas(
        fill_color="rgba(255, 165, 0, 0.3)",
        stroke_width=0,
        background_image=bg_image,
        initial_drawing=initial_drawing,
        drawing_mode="transform",
        height=display_height,
        width=display_width,
        key=f"canvas_{submission_id}_{page_index}"
    )

    # Return current page index for sidebar filtering
    return page_index

def render_enhanced_question_cards(items, existing_gradings, current_page_index=None):
    """Render enhanced question cards with individual regrade functionality (optimized for sidebar)."""

    # Filter items by current page if page_index is provided
    if current_page_index is not None:
        filtered_items = []
        for item in items:
            # Check if this item has answer on current page
            try:
                source_page_index = item.source_page_index
                if source_page_index.isdigit():
                    # Single page format
                    if int(source_page_index) == current_page_index:
                        filtered_items.append(item)
                else:
                    # JSON array format - parse and check
                    page_indices = json.loads(source_page_index)
                    if current_page_index in page_indices:
                        filtered_items.append(item)
            except (ValueError, json.JSONDecodeError, AttributeError):
                # If can't parse, include by default for backward compatibility
                filtered_items.append(item)

        items_to_render = filtered_items

        # Update header with page info and filtering status
        total_questions = len(items)
        page_questions = len(items_to_render)
        st.markdown(f"#### 📝 Chi tiết chấm điểm - Trang {current_page_index + 1}")
        st.caption(f"Hiển thị {page_questions}/{total_questions} câu hỏi có bài làm ở trang này")

        # Show empty state if no questions on this page
        if not items_to_render:
            st.info(f"📄 Không có câu hỏi nào được làm ở trang {current_page_index + 1}")
            st.caption("💡 Hãy chọn trang khác hoặc kiểm tra xem có câu hỏi nào đã được crop chưa")
            return
    else:
        items_to_render = items
        st.markdown("#### 📝 Chi tiết chấm điểm từng câu")

    # Add container for question cards (scrollable by default in sidebar)
    for item in items_to_render:
        grading = existing_gradings.get(item.id)

        if not grading:
            continue

        question_label = format_question_label(item.question.order_index, item.question.part_label)

        # Compact question card
        with st.container(border=True):
            # Header with result and partial credit in single line
            result_icon = "✅" if grading.is_correct else "❌"
            result_text = "ĐÚNG" if grading.is_correct else "SAI"

            # Create two columns for result and partial credit
            col_result, col_partial = st.columns([1, 1])

            with col_result:
                st.markdown(f"**{question_label}** {result_icon} {result_text}")

            with col_partial:
                if grading.partial_credit:
                    st.caption("⚡ Một phần")  # Shortened text

            # Compact regrade button
            if st.button(f"🔄 Chấm lại", key=f"regrade_btn_{item.id}", help=f"Chấm lại {question_label}", use_container_width=True):
                app_state.regrade_item_id = item.id
                st.rerun()

            # Show regrade interface if this question is selected
            if app_state.regrade_item_id == item.id:
                render_regrade_interface(item, grading)

            # Compact error analysis
            render_compact_error_analysis(grading)

def render_regrade_interface(item, grading):
    """Render regrade interface with clarification input."""
    st.markdown("### 📝 Chấm lại với clarification")

    clarify_text = st.text_area(
        "Lời giải thích từ thầy cô (bắt buộc):",
        key=f"clarify_text_{item.id}",
        placeholder="Ví dụ: Ở bước cuối là y^6, không phải y^8",
        help="Nhập clarification để AI hiểu rõ hơn về lỗi cần chú ý"
    )

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("✅ Xác nhận chấm lại", key=f"confirm_regrade_{item.id}", type="primary"):
            if not clarify_text or not clarify_text.strip():
                st.error("Lời giải thích là bắt buộc.")
            else:
                handle_regrade_single_question(item, clarify_text.strip())

    with col2:
        if st.button("❌ Hủy", key=f"cancel_regrade_{item.id}"):
            app_state.regrade_item_id = None
            st.rerun()

def render_compact_error_analysis(grading):
    """Render compact error analysis for sidebar."""
    # Check for categorized errors first
    critical_errors = []
    part_errors = []

    if hasattr(grading, 'critical_errors') and grading.critical_errors:
        try:
            critical_errors = json.loads(grading.critical_errors)
        except (json.JSONDecodeError, TypeError):
            pass

    if hasattr(grading, 'part_errors') and grading.part_errors:
        try:
            part_errors = json.loads(grading.part_errors)
        except (json.JSONDecodeError, TypeError):
            pass

    # Compact error display with colored backgrounds
    if critical_errors:
        for error in critical_errors:
            st.error(f"🔴 {error.get('description', '')}")

    if part_errors:
        for error in part_errors:
            st.warning(f"🟡 {error.get('description', '')}")

    # Fallback to legacy error display (compact)
    if not critical_errors and not part_errors and grading.error_description and grading.error_description != "No errors found":
        st.caption("🔍 **Lỗi:**")
        st.caption(grading.error_description[:100] + "..." if len(grading.error_description) > 100 else grading.error_description)

def render_error_analysis(grading):
    """Render detailed error analysis (legacy function for compatibility)."""
    render_compact_error_analysis(grading)

def handle_regrade_single_question(item, clarify_text):
    """Handle regrading a single question with clarification."""
    with st.spinner("🤖 Đang chấm lại với lời giải thích..."):
        success, msg, _ = grading_service.grade_single_question(item.id, clarify=clarify_text)
        st.toast(msg, icon="✅" if success else "❌")

        if success:
            # Reset regrade state
            app_state.regrade_item_id = None
            st.rerun()

def handle_grade_all_questions(submission_id, items):
    """Handle grading all questions for a submission."""
    with st.spinner(f"🤖 Đang chấm {len(items)} câu hỏi..."):
        success, msg, results = grading_service.grade_submission_batch(submission_id)
        st.toast(msg, icon="✅" if success else "❌")

        if success:
            st.rerun()

def render_individual_grading_interface(items, existing_gradings):
    """Render interface for grading individual questions."""
    st.subheader("📝 Chấm từng câu")
    st.info("Chọn câu hỏi để chấm điểm:")

    for item in items:
        question_label = format_question_label(item.question.order_index, item.question.part_label)
        grading = existing_gradings.get(item.id)

        col1, col2 = st.columns([3, 1])

        with col1:
            if grading:
                status = "✅ Đã chấm" if grading.is_correct else "❌ Đã chấm"
                st.markdown(f"**{question_label}** - {status}")
            else:
                st.markdown(f"**{question_label}** - ⏳ Chưa chấm")

        with col2:
            if st.button(f"🔍 Chấm", key=f"grade_individual_{item.id}"):
                with st.spinner("🤖 Đang chấm điểm..."):
                    success, msg, _ = grading_service.grade_single_question(item.id)
                    st.toast(msg, icon="✅" if success else "❌")

                    if success:
                        st.rerun()