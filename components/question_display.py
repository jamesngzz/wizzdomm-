# components/question_display.py
import streamlit as st
import os
import sys
import json
from typing import Optional, List

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.utils import format_question_label

class QuestionDisplayComponent:
    """Thành phần có thể tái sử dụng để hiển thị câu hỏi và kết quả chấm điểm một cách nhất quán."""

    @staticmethod
    def _render_image(image_path: str, caption: str):
        """Hàm trợ giúp nội bộ để hiển thị một hình ảnh một cách an toàn."""
        if os.path.exists(image_path):
            st.image(image_path, caption=caption)
        else:
            st.error(f"❌ Không tìm thấy hình ảnh: {os.path.basename(image_path)}")

    @staticmethod
    def render_question_preview(
        question_image_path: str,
        question_label: str,
        question_image_paths: Optional[str] = None,
        has_multiple_images: bool = False
    ):
        """Hiển thị (các) hình ảnh câu hỏi với kiểu dáng nhất quán."""
        # Collect all images: primary + additional paths
        all_images = []
        
        # Always include primary image
        if question_image_path:
            all_images.append(question_image_path)
        
        # Add additional images from JSON paths
        if question_image_paths:
            try:
                additional_paths = json.loads(question_image_paths)
                if additional_paths:
                    all_images.extend(additional_paths)
            except (json.JSONDecodeError, TypeError):
                pass  # Just skip additional paths if invalid
        
        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in all_images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        
        # Render all images
        if len(unique_images) > 1:
            st.caption(f"Câu hỏi với {len(unique_images)} hình ảnh:")
            for i, path in enumerate(unique_images):
                QuestionDisplayComponent._render_image(path, caption=f"{question_label} - Hình {i+1}")
        elif unique_images:
            QuestionDisplayComponent._render_image(unique_images[0], caption=f"Câu hỏi {question_label}")
        else:
            st.error(f"Không tìm thấy hình ảnh cho {question_label}")

    @staticmethod
    def render_answer_preview(
        answer_image_path: str,
        answer_label: str,
        answer_image_paths: Optional[str] = None,
        has_multiple_images: bool = False
    ):
        """Hiển thị (các) hình ảnh câu trả lời học sinh với kiểu dáng nhất quán."""
        # Collect all images: primary + additional paths
        all_images = []
        
        # Always include primary image
        if answer_image_path:
            all_images.append(answer_image_path)
        
        # Add additional images from JSON paths
        if answer_image_paths:
            try:
                additional_paths = json.loads(answer_image_paths)
                if additional_paths:
                    all_images.extend(additional_paths)
            except (json.JSONDecodeError, TypeError):
                pass  # Just skip additional paths if invalid
        
        # Remove duplicates while preserving order
        seen = set()
        unique_images = []
        for img in all_images:
            if img not in seen:
                seen.add(img)
                unique_images.append(img)
        
        # Render all images
        if len(unique_images) > 1:
            st.caption(f"Câu trả lời học sinh với {len(unique_images)} hình ảnh:")
            for i, path in enumerate(unique_images):
                QuestionDisplayComponent._render_image(path, caption=f"Câu trả lời - Hình {i+1}")
        elif unique_images:
            QuestionDisplayComponent._render_image(unique_images[0], caption=answer_label)
        else:
            st.error(f"Không tìm thấy hình ảnh câu trả lời")

    @staticmethod
    def render_grading_summary(grading_result, show_details: bool = True, editable: bool = False):
        """Hiển thị tóm tắt chi tiết của kết quả chấm điểm."""
        st.markdown("**🎯 Kết quả chấm điểm AI**")
        
        # Display main result
        if grading_result.is_correct:
            st.success("**Kết quả: ĐÚNG** ✅")
        else:
            st.error("**Kết quả: SAI** ❌")
        
        if grading_result.partial_credit:
            st.info("ℹ️ Được đề xuất chấm điểm một phần cho câu trả lời này.")

        # Display new categorized error analysis
        if show_details:
            # Check for new error format first
            critical_errors = []
            part_errors = []

            if hasattr(grading_result, 'critical_errors') and grading_result.critical_errors:
                try:
                    critical_errors = json.loads(grading_result.critical_errors)
                except (json.JSONDecodeError, TypeError):
                    pass

            if hasattr(grading_result, 'part_errors') and grading_result.part_errors:
                try:
                    part_errors = json.loads(grading_result.part_errors)
                except (json.JSONDecodeError, TypeError):
                    pass

            # Display critical errors (red)
            if critical_errors:
                with st.container(border=True):
                    st.markdown("**🔴 Lỗi nghiêm trọng (Lỗi chí mạng):**")
                    for error in critical_errors:
                        st.error(f"**{error.get('description', '')}**")
                        if error.get('phrases'):
                            for phrase in error['phrases']:
                                st.markdown(f"- {phrase}")

            # Display part errors (yellow/warning)
            if part_errors:
                with st.container(border=True):
                    st.markdown("**🟡 Lỗi một phần (Lỗi nhỏ/Không chắc chắn):**")
                    for error in part_errors:
                        st.warning(f"**{error.get('description', '')}**")
                        if error.get('phrases'):
                            for phrase in error['phrases']:
                                st.markdown(f"- {phrase}")

            # Fallback to legacy error display if new format not available
            if not critical_errors and not part_errors and grading_result.error_description and grading_result.error_description != "No errors found":
                with st.container(border=True):
                    st.markdown("**🔍 Phân tích lỗi (Cũ):**")
                    st.warning(grading_result.error_description)

                    if hasattr(grading_result, 'error_phrases') and grading_result.error_phrases:
                        try:
                            phrases = json.loads(grading_result.error_phrases)
                            if phrases:
                                st.markdown("**Các điểm lỗi chính:**")
                                for phrase in phrases:
                                    st.markdown(f"- {phrase}")
                        except (json.JSONDecodeError, TypeError):
                            pass
        
        return None  # No save requested
