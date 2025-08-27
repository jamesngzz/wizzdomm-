# pages/digitize_exam_page.py
import streamlit as st
import os
import sys
import time
from PIL import Image
from streamlit_cropper import st_cropper
import json

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.state_manager import app_state
from services.exam_service import ExamService
from services.question_service import QuestionService
from components.shared_components import render_selection_box, render_confirmation_dialog
from core.utils import format_question_label

def show_digitize_exam_page():
    """Page for digitizing exams, using shared components for selection and deletion."""
    st.header("✂️ Digitize Exam Questions")
    st.markdown("Crop individual questions from the exam paper to create a structured question bank.")

    # --- Exam Selection ---
    st.subheader("📚 Select Exam to Digitize")

    success, _, exams = ExamService.get_exam_list()
    if not exams:
        st.warning("⚠️ No exams found. Please create an exam first.")
        if st.button("➕ Create New Exam"):
            app_state.page = "📝 Create Exam"
            st.rerun()
        return

    selected_exam = render_selection_box(
        label="Choose an exam to digitize:",
        options=exams,
        format_func=lambda exam: f"{exam['name']} - {exam.get('topic', 'N/A')} (ID: {exam['id']})",
        key="digitize_exam_selector"
    )

    if not selected_exam:
        return
        
    app_state.current_exam_id = selected_exam['id']

    # --- Delete Confirmation Dialog Logic ---
    if app_state.question_to_delete:
        question_info = app_state.question_to_delete
        
        def confirm_delete():
            success, msg, _ = QuestionService.delete_question(question_info['id'])
            st.toast(msg, icon="✅" if success else "❌")
            app_state.question_to_delete = None

        def cancel_delete():
            app_state.question_to_delete = None

        render_confirmation_dialog(
            item_name=question_info['label'],
            on_confirm=confirm_delete,
            on_cancel=cancel_delete,
            dialog_key=f"delete_q_{question_info['id']}"
        )
        st.divider()

    # --- Display Existing Questions ---
    success, _, questions = QuestionService.get_questions_by_exam(app_state.current_exam_id)
    if questions:
        with st.expander(f"📋 View Existing Questions ({len(questions)})"):
            for q in questions:
                label = format_question_label(q.order_index, q.part_label)
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{label}**")
                with col2:
                    st.image(q.question_image_path, width=100)
                with col3:
                    if st.button("🗑️ Delete", key=f"delete_btn_{q.id}", help=f"Delete {label}"):
                        app_state.question_to_delete = {'id': q.id, 'label': label}
                        st.rerun()
    st.divider()

    # --- Cropping Interface ---
    display_cropping_interface()

def display_cropping_interface():
    """Renders the main image cropping UI."""
    exam_details = ExamService.get_exam_details(app_state.current_exam_id)[2]
    if not exam_details or not exam_details.original_image_paths:
        st.warning("This exam has no images to digitize.")
        return

    try:
        image_paths = json.loads(exam_details.original_image_paths or '[]')
    except (json.JSONDecodeError, TypeError):
        image_paths = []

    if not image_paths:
        st.error("Không tìm thấy ảnh nào cho kỳ thi này.")
        return
    
    # Page navigation for multi-page exams
    page_index = st.number_input(
        f"Select page (1 to {len(image_paths)})", 
        min_value=1, max_value=len(image_paths), value=1, 
        help="Select which page of the exam paper to crop from."
    ) - 1

    current_image_path = image_paths[page_index]
    if not os.path.exists(current_image_path):
        st.error(f"Image not found: {current_image_path}")
        return

    img = Image.open(current_image_path)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**🎯 Crop a question area:**")
        cropped_img = st_cropper(img, realtime_update=True, box_color="#0066CC", return_type="image")

    with col2:
        st.markdown("**📝 Question Details:**")
        if cropped_img:
            st.image(cropped_img, caption="Cropped Preview", use_column_width=True)
        
        with st.form("question_form"):
            question_label = st.text_input("Question Label*", placeholder="e.g., 1a, 2b, 3")
            submitted = st.form_submit_button("💾 Save Question", type="primary")

            if submitted:
                if not question_label.strip():
                    st.error("Question label cannot be empty.")
                elif cropped_img:
                    with st.spinner("Saving question..."):
                        success, message, _ = QuestionService.create_question(
                            exam_id=app_state.current_exam_id,
                            question_label=question_label,
                            cropped_images=[cropped_img] 
                        )
                        if success:
                            st.success(message)
                            st.balloons()
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(message)