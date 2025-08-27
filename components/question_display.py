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
    """Reusable component for displaying questions and grading results consistently."""

    @staticmethod
    def _render_image(image_path: str, caption: str):
        """Internal helper to render a single image safely."""
        if os.path.exists(image_path):
            st.image(image_path, caption=caption, use_column_width=True)
        else:
            st.error(f"❌ Image not found: {os.path.basename(image_path)}")

    @staticmethod
    def render_question_preview(
        question_image_path: str,
        question_label: str,
        question_image_paths: Optional[str] = None,
        has_multiple_images: bool = False
    ):
        """Renders question image(s) with consistent styling."""
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
            st.caption(f"Question with {len(unique_images)} images:")
            for i, path in enumerate(unique_images):
                QuestionDisplayComponent._render_image(path, caption=f"{question_label} - Image {i+1}")
        elif unique_images:
            QuestionDisplayComponent._render_image(unique_images[0], caption=f"Question {question_label}")
        else:
            st.error(f"No images found for {question_label}")

    @staticmethod
    def render_answer_preview(
        answer_image_path: str,
        answer_label: str,
        answer_image_paths: Optional[str] = None,
        has_multiple_images: bool = False
    ):
        """Renders student answer image(s) with consistent styling."""
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
            st.caption(f"Student answer with {len(unique_images)} images:")
            for i, path in enumerate(unique_images):
                QuestionDisplayComponent._render_image(path, caption=f"Answer - Image {i+1}")
        elif unique_images:
            QuestionDisplayComponent._render_image(unique_images[0], caption=answer_label)
        else:
            st.error(f"No answer images found")

    @staticmethod
    def render_grading_summary(grading_result, show_details: bool = True, editable: bool = False):
        """Renders a detailed summary of a grading result."""
        st.markdown("**🎯 AI Grading Result**")
        
        # Display main result and confidence
        col1, col2 = st.columns(2)
        with col1:
            if grading_result.is_correct:
                st.success("**Result: CORRECT** ✅")
            else:
                st.error("**Result: INCORRECT** ❌")
        
        with col2:
            if grading_result.confidence:
                st.metric("AI Confidence", f"{grading_result.confidence:.1%}")
        
        if grading_result.partial_credit:
            st.info("ℹ️ Partial credit was suggested for this answer.")

        # Display detailed error analysis
        if show_details and grading_result.error_description and grading_result.error_description != "No errors found":
            with st.container(border=True):
                st.markdown("**🔍 Error Analysis:**")
                
                if editable:
                    # Editable mode
                    new_analysis = st.text_area(
                        "Edit Error Analysis:",
                        value=grading_result.error_description,
                        key=f"analysis_{grading_result.id}",
                        height=100
                    )
                    
                    # Handle error phrases
                    current_phrases = []
                    if hasattr(grading_result, 'error_phrases') and grading_result.error_phrases:
                        try:
                            current_phrases = json.loads(grading_result.error_phrases)
                        except (json.JSONDecodeError, TypeError):
                            current_phrases = []
                    
                    st.markdown("**Key Error Points:**")
                    phrases_text = st.text_area(
                        "Edit Key Error Points (one per line):",
                        value="\n".join(current_phrases) if current_phrases else "",
                        key=f"phrases_{grading_result.id}",
                        height=80
                    )
                    
                    # Save button
                    if st.button("💾 Save Changes", key=f"save_{grading_result.id}", type="primary"):
                        return {
                            'save_requested': True,
                            'grading_id': grading_result.id,
                            'new_analysis': new_analysis,
                            'new_phrases': [p.strip() for p in phrases_text.split('\n') if p.strip()]
                        }
                else:
                    # Display mode
                    st.warning(grading_result.error_description)
                    
                    if hasattr(grading_result, 'error_phrases') and grading_result.error_phrases:
                        try:
                            phrases = json.loads(grading_result.error_phrases)
                            if phrases:
                                st.markdown("**Key error points:**")
                                for phrase in phrases:
                                    st.markdown(f"- {phrase}")
                        except (json.JSONDecodeError, TypeError):
                            pass # Ignore if error_phrases is not valid JSON
        
        return None  # No save requested