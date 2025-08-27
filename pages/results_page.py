# pages/results_page.py
import streamlit as st
import os
import sys
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.submission_service import SubmissionService
from services.results_service import results_service
from components.shared_components import render_selection_box
from components.canvas_helper import CanvasHelper

def show_results_page():
    """
    Page for viewing overall results and generating reports.
    Step 2: Interactive canvas for visual feedback.
    """
    st.header("📊 Results & Reports")
    st.markdown("Review the AI results and provide visual feedback by dragging annotations onto the answer sheet.")

    sub_success, _, submissions = SubmissionService.get_all_submissions_with_answers()
    
    if not submissions:
        st.warning("⚠️ No graded submissions found. Please grade a submission first.")
        return

    st.subheader("📋 Select a Submission to Review")
    selected_submission_data = render_selection_box(
        label="Choose a submission:",
        options=submissions,
        format_func=lambda s: f"{s['submission'].student_name} - {s['exam_name']} (ID: {s['submission'].id})",
        key="results_submission_selector"
    )

    if not selected_submission_data:
        st.info("Select a submission from the dropdown above to see the results.")
        return

    st.divider()

    submission_id = selected_submission_data['submission'].id
    results_data = results_service.get_results_for_submission(submission_id)

    if not results_data:
        st.error("Could not load results for this submission.")
        return
        
    st.header(f"Results for: {results_data['student_name']}")
    st.caption(f"Exam: {results_data['exam_name']}")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("✍️ Visual Feedback Canvas")
        image_paths = results_data['submission_image_paths']
        
        if not image_paths:
            st.warning("No answer sheet images found for this submission.")
        else:
            page_index = 0
            if len(image_paths) > 1:
                page_selection = st.selectbox(
                    "Select page to annotate:", 
                    options=[f"Page {i+1}" for i in range(len(image_paths))],
                    key=f"page_select_{submission_id}"
                )
                page_index = int(page_selection.split(" ")[1]) - 1

            try:
                bg_image = Image.open(image_paths[page_index]).convert("RGBA")
            except FileNotFoundError:
                st.error(f"Image not found at path: {image_paths[page_index]}")
                return

            initial_drawing = CanvasHelper.generate_initial_drawing(
                graded_items=results_data['graded_items'],
                current_page_index=page_index
            )

            st.info("Drag and drop the colored boxes to the correct positions on the answer sheet.")
            # Scale image to fit container while maintaining aspect ratio
            max_width = 800  # Maximum width for better viewing
            scale_factor = min(max_width / bg_image.width, 1.0)  # Don't upscale
            display_width = int(bg_image.width * scale_factor)
            display_height = int(bg_image.height * scale_factor)
            
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=0,
                background_image=bg_image,
                initial_drawing=st.session_state.get(f"canvas_json_{submission_id}_{page_index}", initial_drawing),
                drawing_mode="transform",
                height=display_height,
                width=display_width,
                key=f"canvas_{submission_id}_{page_index}"
            )
            
            # Only update session state if canvas data actually changed
            if canvas_result.json_data is not None:
                current_key = f"canvas_json_{submission_id}_{page_index}"
                if current_key not in st.session_state or st.session_state[current_key] != canvas_result.json_data:
                    st.session_state[current_key] = canvas_result.json_data

    with col2:
        st.subheader("🎯 Grading Summary")
        graded_items = results_data['graded_items']
        
        # Filter items for current page only
        items_for_current_page = [
            item for item in graded_items 
            if item.get('source_page_index') == page_index
        ]
        
        if not graded_items:
            st.info("This submission has not been graded yet.")
        elif not items_for_current_page:
            st.info(f"No graded questions found for page {page_index + 1}.")
        else:
            for item in items_for_current_page:
                with st.container(border=True):
                    st.markdown(f"**{item['question_label']}**")
                    if item['is_correct']:
                        st.success("**Result: CORRECT** ✅")
                    else:
                        st.error("**Result: INCORRECT** ❌")
                    if item['confidence']:
                        st.metric("AI Confidence", f"{item['confidence']:.1%}")
                    if not item['is_correct']:
                        if item['partial_credit']:
                            st.info("ℹ️ Partial credit was suggested.")
                        if item['error_description']:
                            st.warning(f"**Analysis:** {item['error_description']}")
                        if item['error_phrases']:
                            st.markdown("**Key Errors:**")
                            for phrase in item['error_phrases']:
                                st.markdown(f"- _{phrase}_")
                st.markdown("---")