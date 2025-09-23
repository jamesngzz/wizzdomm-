# components/grading_interface.py
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple, Callable

from .shared_components import render_selection_box
from .question_display import QuestionDisplayComponent
from core.utils import format_question_label

class GradingInterfaceComponent:
    """Các thành phần giao diện có thể tái sử dụng dành riêng cho quy trình chấm điểm."""

    @staticmethod
    def render_progress_tracker(
        graded_count: int,
        total_count: int,
        correct_count: Optional[int] = None
    ):
        """Hiển thị thanh tiến độ chấm điểm và các chỉ số."""
        progress = graded_count / total_count if total_count > 0 else 0
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(progress, text=f"Tiến độ: {graded_count}/{total_count} câu hỏi đã chấm")
        with col2:
            if graded_count == total_count and total_count > 0:
                st.success("✅ Hoàn thành!")
            else:
                st.info(f"⏳ Còn lại {total_count - graded_count}")
        
        if correct_count is not None and graded_count > 0:
            accuracy = correct_count / graded_count * 100
            st.metric("Độ chính xác tổng thể", f"{accuracy:.1f}%", help=f"{correct_count}/{graded_count} đúng")

    @staticmethod
    def render_batch_controls(
        graded_count: int,
        total_count: int,
        grading_in_progress: bool,
        batch_callback: Callable,
        regrade_callback: Callable
    ):
        """Hiển thị các nút cho các thao tác chấm điểm hàng loạt."""
        st.markdown("### ⚡ Xử lý hàng loạt")
        col1, col2 = st.columns(2)
        
        with col1:
            remaining = total_count - graded_count
            button_disabled = grading_in_progress or remaining == 0
            if st.button(f"🚀 Chấm tất cả còn lại ({remaining})", type="primary", disabled=button_disabled):
                batch_callback()
                st.rerun()
        
        with col2:
            button_disabled = grading_in_progress or graded_count == 0
            if st.button("🔄 Chấm lại tất cả câu hỏi", disabled=button_disabled):
                regrade_callback()
                # No rerun here, callback should handle it

    @staticmethod
    def render_submission_selector(
        submissions_data: List[Dict[str, Any]],
        key: str
    ) -> Tuple[Optional[Dict], int]:
        """Hiển thị danh sách chọn bài làm sử dụng thành phần chia sẻ."""
        if not submissions_data:
            return None, -1

        selected_data = render_selection_box(
            label="Chọn bài làm để chấm:",
            options=submissions_data,
            format_func=lambda data: (
                f"{data['submission'].student_name} - {data.get('exam_name', 'N/A')} "
                f"({len(data['items'])} câu hỏi)"
            ),
            key=key
        )
        
        if selected_data:
            GradingInterfaceComponent._render_submission_details(selected_data)
            selected_index = submissions_data.index(selected_data)
            return selected_data, selected_index
        
        return None, -1

    @staticmethod
    def _render_submission_details(submission_data: Dict[str, Any]):
        """Hiển thị các thẻ chỉ số với chi tiết về bài làm được chọn."""
        col1, col2, col3 = st.columns(3)
        col1.metric("Học sinh", submission_data['submission'].student_name)
        col2.metric("Đề thi", submission_data.get('exam_name', 'Không rõ'))
        col3.metric("Câu hỏi", len(submission_data['items']))

    @staticmethod
    def render_question_grading_card(
        submission_item,
        question,
        existing_grading=None,
        grade_callback: Optional[Callable] = None,
        delete_callback: Optional[Callable] = None
    ):
        """Hiển thị thẻ có thể mở rộng cho việc chấm điểm một câu hỏi."""
        question_label = format_question_label(question.order_index, question.part_label)
        status_icon = '✅' if existing_grading else '⏳'
        
        with st.expander(f"Câu hỏi {question_label} {status_icon}", expanded=not existing_grading):
            col1, col2 = st.columns([4, 1])
            with col2:
                if delete_callback:
                    if st.button("🗑️ Xóa câu hỏi", key=f"delete_q_{question.id}", help=f"Xóa {question_label} khỏi toàn bộ đề thi"):
                        delete_callback(question, question_label)

            # Display question and answer images side-by-side
            img_col1, img_col2 = st.columns(2)
            with img_col1:
                st.markdown("**📝 Câu hỏi**")
                QuestionDisplayComponent.render_question_preview(
                    question.question_image_path, question_label, 
                    question_image_paths=question.question_image_paths,
                    has_multiple_images=question.has_multiple_images
                )
            with img_col2:
                st.markdown("**✍️ Câu trả lời học sinh**")
                QuestionDisplayComponent.render_answer_preview(
                    submission_item.answer_image_path, "Câu trả lời học sinh",
                    answer_image_paths=submission_item.answer_image_paths,
                    has_multiple_images=submission_item.has_multiple_images
                )

            st.markdown("---")
            
            # Display grading result or grading buttons
            if existing_grading:
                # Check if edit mode is enabled
                edit_mode = st.checkbox("✏️ Chế độ chỉnh sửa", key=f"edit_mode_{submission_item.id}")
                
                # Render grading summary with edit capability
                save_result = QuestionDisplayComponent.render_grading_summary(
                    existing_grading, 
                    show_details=True, 
                    editable=edit_mode
                )
                
                # Handle save request
                if save_result and save_result.get('save_requested'):
                    from database.manager_v2 import db_manager
                    success = db_manager.update_grading(
                        grading_id=save_result['grading_id'],
                        error_description=save_result['new_analysis'],
                        error_phrases=save_result['new_phrases']
                    )
                    if success:
                        st.success("✅ Lưu thay đổi thành công!")
                        st.rerun()
                    else:
                        st.error("❌ Không thể lưu thay đổi.")
                
            else:
                st.info("Câu hỏi này chưa được chấm điểm.")
                if grade_callback:
                    if st.button(f"🚀 Chấm câu hỏi {question_label}", type="primary", key=f"grade_{submission_item.id}"):
                        grade_callback(submission_item, question)