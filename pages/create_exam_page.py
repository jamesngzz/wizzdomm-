# pages/create_exam_page.py
import streamlit as st
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.state_manager import app_state
from services.exam_service import ExamService
from services.image_service import ImageService
from components.file_uploader import FileUploaderComponent

def show_create_exam_page():
    """Page for creating new exams, using the service layer for all logic."""
    st.header("📝 Create New Exam")
    st.markdown("Start by uploading exam paper images and entering basic information.")

    # Exam creation form
    with st.form("create_exam_form"):
        uploaded_files, exam_name, topic, grade_level = FileUploaderComponent.render_exam_uploader("create_exam")
        submit_button = st.form_submit_button("🚀 Create Exam", type="primary")

        if submit_button:
            # 1. Save images via the ImageService
            img_success, img_message, saved_paths = ImageService.save_uploaded_exam_images(
                uploaded_files, exam_name
            )

            if not img_success:
                st.error(f"❌ Image processing failed: {img_message}")
            else:
                # 2. Create exam record via the ExamService
                create_success, create_message, exam_id = ExamService.create_exam(
                    name=exam_name,
                    topic=topic,
                    grade_level=grade_level,
                    image_paths=saved_paths
                )

                if create_success:
                    app_state.current_exam_id = exam_id
                    st.success(f"✅ {create_message}")
                    st.info("🎯 Next step: Go to 'Digitize Exam' to crop individual questions.")
                else:
                    st.error(f"❌ Exam creation failed: {create_message}")

    # --- Show existing exams ---
    st.divider()
    st.subheader("📚 Existing Exams")

    try:
        success, message, exams = ExamService.get_exam_list()
        if not success:
            st.error(message)
            return

        if exams:
            # Display the last 10 exams
            for exam in exams[:10]:
                col1, col2 = st.columns([4, 1])
                with col1:
                    display_text = (f"📝 **{exam['name']}** - {exam.get('topic', 'N/A')} "
                                    f"({exam['question_count']} questions)")
                    st.write(display_text)

                with col2:
                    if st.button("📋 Details", key=f"details_{exam['id']}", help="View details"):
                        # Toggle details view using the centralized state
                        if app_state.selected_exam_details == exam['id']:
                            app_state.selected_exam_details = None
                        else:
                            app_state.selected_exam_details = exam['id']
                        st.rerun()

                # Expanded view for the selected exam
                if app_state.selected_exam_details == exam['id']:
                    with st.container(border=True):
                        st.write(f"**Topic:** {exam.get('topic', 'N/A')}")
                        st.write(f"**Grade Level:** {exam.get('grade_level', 'N/A')}")
                        st.write(f"**Questions Digitized:** {exam['question_count']}")
                        st.write(f"**Created:** {exam['created_at'].strftime('%Y-%m-%d %H:%M')}")
                        
                        if st.button(f"✂️ Digitize This Exam", key=f"digitize_{exam['id']}"):
                            app_state.current_exam_id = exam['id']
                            app_state.page = "✂️ Digitize Exam"
                            st.rerun()
        else:
            st.info("No exams created yet. Create your first exam above!")

    except Exception as e:
        st.error(f"An error occurred while displaying exams: {e}")