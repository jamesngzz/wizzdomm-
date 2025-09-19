# components/grading_interface.py
import streamlit as st
from typing import List, Dict, Any, Optional, Tuple, Callable

from .shared_components import render_selection_box
from .question_display import QuestionDisplayComponent
from core.utils import format_question_label

class GradingInterfaceComponent:
    """Reusable UI components specifically for the grading workflow."""

    @staticmethod
    def render_progress_tracker(
        graded_count: int,
        total_count: int,
        correct_count: Optional[int] = None
    ):
        """Renders the grading progress bar and metrics."""
        progress = graded_count / total_count if total_count > 0 else 0
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.progress(progress, text=f"Progress: {graded_count}/{total_count} questions graded")
        with col2:
            if graded_count == total_count and total_count > 0:
                st.success("✅ Complete!")
            else:
                st.info(f"⏳ {total_count - graded_count} remaining")
        
        if correct_count is not None and graded_count > 0:
            accuracy = correct_count / graded_count * 100
            st.metric("Overall Accuracy", f"{accuracy:.1f}%", help=f"{correct_count}/{graded_count} correct")

    @staticmethod
    def render_batch_controls(
        graded_count: int,
        total_count: int,
        grading_in_progress: bool,
        batch_callback: Callable,
        regrade_callback: Callable
    ):
        """Renders buttons for batch grading operations."""
        st.markdown("### ⚡ Batch Processing")
        col1, col2 = st.columns(2)
        
        with col1:
            remaining = total_count - graded_count
            button_disabled = grading_in_progress or remaining == 0
            if st.button(f"🚀 Grade All Remaining ({remaining})", type="primary", disabled=button_disabled):
                batch_callback()
                st.rerun()
        
        with col2:
            button_disabled = grading_in_progress or graded_count == 0
            if st.button("🔄 Re-grade All Questions", disabled=button_disabled):
                regrade_callback()
                # No rerun here, callback should handle it

    @staticmethod
    def render_submission_selector(
        submissions_data: List[Dict[str, Any]],
        key: str
    ) -> Tuple[Optional[Dict], int]:
        """Renders the submission selection dropdown using the shared component."""
        if not submissions_data:
            return None, -1

        selected_data = render_selection_box(
            label="Choose submission to grade:",
            options=submissions_data,
            format_func=lambda data: (
                f"{data['submission'].student_name} - {data.get('exam_name', 'N/A')} "
                f"({len(data['items'])} questions)"
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
        """Displays metric cards with details about the selected submission."""
        col1, col2, col3 = st.columns(3)
        col1.metric("Student", submission_data['submission'].student_name)
        col2.metric("Exam", submission_data.get('exam_name', 'Unknown'))
        col3.metric("Questions", len(submission_data['items']))

    @staticmethod
    def render_question_grading_card(
        submission_item,
        question,
        existing_grading=None,
        grade_callback: Optional[Callable] = None,
        delete_callback: Optional[Callable] = None
    ):
        """Renders an expandable card for grading a single question."""
        question_label = format_question_label(question.order_index, question.part_label)
        status_icon = '✅' if existing_grading else '⏳'
        
        with st.expander(f"Question {question_label} {status_icon}", expanded=not existing_grading):
            col1, col2 = st.columns([4, 1])
            with col2:
                if delete_callback:
                    if st.button("🗑️ Delete Question", key=f"delete_q_{question.id}", help=f"Delete {question_label} from the entire exam"):
                        delete_callback(question, question_label)

            # Display question and answer images side-by-side
            img_col1, img_col2 = st.columns(2)
            with img_col1:
                st.markdown("**📝 Question**")
                QuestionDisplayComponent.render_question_preview(
                    question.question_image_path, question_label, 
                    question_image_paths=question.question_image_paths,
                    has_multiple_images=question.has_multiple_images
                )
            with img_col2:
                st.markdown("**✍️ Student's Answer**")
                QuestionDisplayComponent.render_answer_preview(
                    submission_item.answer_image_path, "Student's Answer",
                    answer_image_paths=submission_item.answer_image_paths,
                    has_multiple_images=submission_item.has_multiple_images
                )

            st.markdown("---")
            
            # Display grading result or grading buttons
            if existing_grading:
                # Check if edit mode is enabled
                edit_mode = st.checkbox("✏️ Edit Mode", key=f"edit_mode_{submission_item.id}")
                
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
                        st.success("✅ Changes saved successfully!")
                        st.rerun()
                    else:
                        st.error("❌ Failed to save changes.")
                
            else:
                st.info("This question has not been graded yet.")
                if grade_callback:
                    if st.button(f"🚀 Grade Question {question_label}", type="primary", key=f"grade_{submission_item.id}"):
                        grade_callback(submission_item, question)