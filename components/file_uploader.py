# components/file_uploader.py
import streamlit as st
from typing import List, Tuple, Dict, Any
from PIL import Image

from core.config import SUPPORTED_IMAGE_FORMATS, MAX_IMAGE_SIZE_MB

class FileUploaderComponent:
    """
    A reusable UI component for handling file uploads with validation and previews.
    This component focuses on rendering widgets and returning user inputs.
    """

    @staticmethod
    def _render_image_previews(uploaded_files: List, preview_columns: int):
        """Renders a grid of image previews."""
        st.markdown("**Image Previews:**")
        cols = st.columns(preview_columns)
        for i, uploaded_file in enumerate(uploaded_files):
            with cols[i % preview_columns]:
                try:
                    image = Image.open(uploaded_file)
                    st.image(image, caption=uploaded_file.name, use_column_width=True)
                except Exception as e:
                    st.error(f"Failed to preview {uploaded_file.name}: {e}")

    @staticmethod
    def render_image_uploader(
        label: str,
        help_text: str = None,
        key: str = None
    ) -> List:
        """
        Renders a generic image uploader widget.
        Validation logic is now primarily handled by the service layer.
        """
        if help_text is None:
            help_text = (f"Supported formats: {', '.join(SUPPORTED_IMAGE_FORMATS).upper()}. "
                         f"Max size: {MAX_IMAGE_SIZE_MB}MB per file.")

        uploaded_files = st.file_uploader(
            label=label,
            type=SUPPORTED_IMAGE_FORMATS,
            accept_multiple_files=True,
            help=help_text,
            key=key
        )
        return uploaded_files or []

    @staticmethod
    def render_exam_uploader(key_suffix: str) -> Tuple[List, str, str, str]:
        """
        Renders the specific UI for creating an exam, including metadata inputs.
        
        Returns:
            A tuple containing (uploaded_files, exam_name, topic, grade_level).
        """
        st.subheader("📋 Exam Information")
        col1, col2 = st.columns(2)
        with col1:
            exam_name = st.text_input(
                "Exam Name*",
                placeholder="e.g., Midterm Exam I",
                key=f"exam_name_{key_suffix}"
            )
            topic = st.text_input(
                "Topic*",
                placeholder="e.g., Quadratic Equations, Geometry",
                key=f"topic_{key_suffix}"
            )
        with col2:
            grade_level = st.selectbox(
                "Grade Level*",
                options=[f"Grade {i}" for i in range(6, 13)],
                index=4,  # Default to Grade 10
                key=f"grade_{key_suffix}"
            )
        
        st.subheader("📷 Upload Exam Images")
        uploaded_files = FileUploaderComponent.render_image_uploader(
            label="Upload one or more pages of the exam paper.*",
            key=f"exam_uploader_{key_suffix}"
        )

        if uploaded_files:
            FileUploaderComponent._render_image_previews(uploaded_files, preview_columns=4)

        return uploaded_files, exam_name, topic, grade_level