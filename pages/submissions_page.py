# pages/submissions_page.py
import streamlit as st
import os
import sys
from PIL import Image
import json
from streamlit_cropper import st_cropper

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.state_manager import app_state
from services.exam_service import ExamService
from services.submission_service import SubmissionService
from services.question_service import QuestionService
from components.shared_components import render_selection_box
from core.utils import format_question_label
from database.manager_v2 import db_manager # Import db_manager để truy vấn

def show_submissions_page():
    """Page for managing student submissions and mapping answers."""
    
    # Nếu đang ở chế độ ánh xạ, chỉ hiển thị giao diện ánh xạ để tập trung
    if app_state.mapping_mode and app_state.current_submission_id:
        show_answer_mapping_interface()
        return

    # --- Giao diện chính khi không ở chế độ ánh xạ ---
    st.header("👥 Student Submissions")
    st.markdown("Select an exam to view existing submissions or create a new one.")

    # --- 1. Exam Selection (Bước chọn kỳ thi) ---
    exam_success, _, exams = ExamService.get_exam_list()
    if not exams:
        st.warning("⚠️ No exams found. Please create an exam first.")
        return

    selected_exam = render_selection_box(
        label="Choose an exam:",
        options=exams,
        format_func=lambda e: f"{e['name']} - {e.get('topic', 'N/A')} (ID: {e['id']})",
        key="submission_exam_selector"
    )
    if not selected_exam:
        st.info("Please select an exam to proceed.")
        return

    selected_exam_id = selected_exam['id']

    st.divider()

    # --- 2. Display Existing Submissions for the selected exam ---
    st.subheader(f"📚 Existing Submissions for '{selected_exam['name']}'")
    
    # Lấy các submission đã lọc theo exam_id
    submissions_for_exam = db_manager.list_submissions_by_exam(selected_exam_id)

    if not submissions_for_exam:
        st.info("No submissions have been created for this exam yet. Use the form below to create one.")
    else:
        for sub_info in submissions_for_exam:
            sub_id = sub_info['id']
            # Lấy thông tin tiến độ
            #_, _, progress = SubmissionService.get_submission_progress(sub_id)
            
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.markdown(f"**🧑‍🎓 {sub_info['student_name']}**")
                st.caption(f"Submitted on: {sub_info['created_at'].strftime('%Y-%m-%d %H:%M')}")
            with col2:
                # Hiển thị số lượng item đã ánh xạ là đủ ở đây
                item_count = sub_info['item_count']
                st.markdown(f"**Mapped Answers:** {item_count}")

            with col3:
                # Thêm khoảng trống để căn chỉnh
                st.markdown("") 
                st.markdown("")
                if st.button("📝 Continue Mapping", key=f"map_{sub_id}"):
                    app_state.current_submission_id = sub_id
                    app_state.mapping_mode = True
                    st.rerun()

    st.divider()

    # --- 3. Create New Submission Section (Form tạo mới) ---
    with st.expander("📝 Create New Submission for this Exam", expanded=not submissions_for_exam):
        student_name = st.text_input("Student Name*", placeholder="Nguyễn Văn A", key="new_student_name")
        uploaded_files = st.file_uploader(
            "Upload Answer Sheet(s)*",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="new_submission_uploader"
        )
        
        # Preview uploaded images
        if uploaded_files:
            st.markdown("**Image Previews:**")
            cols = st.columns(4)
            for i, uploaded_file in enumerate(uploaded_files):
                with cols[i % 4]:
                    try:
                        image = Image.open(uploaded_file)
                        st.image(image, caption=uploaded_file.name, width="stretch")
                    except Exception as e:
                        st.error(f"Failed to preview {uploaded_file.name}: {e}")

        if st.button("🚀 Create Submission", type="primary"):
            success, message, sub_id = SubmissionService.create_submission(
                exam_id=selected_exam_id,
                student_name=student_name,
                uploaded_files=uploaded_files
            )
            if success:
                st.success(message)
                # Chuyển ngay sang chế độ ánh xạ cho submission vừa tạo
                app_state.current_submission_id = sub_id
                app_state.mapping_mode = True
                st.rerun()
            else:
                st.error(f"❌ Submission failed: {message}")

def show_answer_mapping_interface():
    """Shows the UI for mapping answers for the submission stored in the app state."""
    sub_id = app_state.current_submission_id
    success, msg, progress = SubmissionService.get_submission_progress(sub_id)

    if not success or not progress:
        st.error(f"Error loading submission data: {msg}")
        # Nút để thoát khỏi chế độ ánh xạ nếu có lỗi
        if st.button("🔙 Go Back"):
            app_state.mapping_mode = False
            app_state.current_submission_id = None
            st.rerun()
        return
    
    st.header("✂️ Answer Mapping")
    st.info(f"**Mapping for:** {progress['student_name']} | "
            f"**Exam:** {progress['submission'].exam.name} | "
            f"**Progress:** {progress['mapped_answers']}/{progress['total_questions']} questions mapped.")

    if st.button("✅ Finish Mapping & Return to List"):
        app_state.mapping_mode = False
        app_state.current_submission_id = None
        st.rerun()

    q_success, _, questions = QuestionService.get_questions_by_exam(progress['submission'].exam_id)
    mapped_ids = {item.question_id for item in progress['items']}
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Questions to Map**")
        for q in questions:
            is_mapped = q.id in mapped_ids
            status_icon = "✅" if is_mapped else "⏳"
            label = format_question_label(q.order_index, q.part_label)
            # Dùng st.radio để tự động quản lý trạng thái câu hỏi được chọn
            if st.button(f"{status_icon} {label}", key=f"map_btn_{q.id}", use_container_width=True):
                app_state.selected_question_for_mapping = q.id
                st.rerun() # Rerun để cập nhật cột bên phải
    
    with col2:
        st.markdown("**Crop Student's Answer**")
        if app_state.selected_question_for_mapping:
            display_answer_cropping_ui(progress)
        else:
            st.info("👈 Select a question from the left to map its answer.")

def display_answer_cropping_ui(progress_data):
    """Renders the answer cropping interface for the selected question."""
    question_id = app_state.selected_question_for_mapping
    success, msg, question = QuestionService.get_question_by_id(question_id)
    
    if not success or not question:
        st.error(f"Could not load question data: {msg}")
        return

    st.success(f"Mapping answer for: **{format_question_label(question.order_index, question.part_label)}**")
    
    with st.expander("Show Question Reference"):
        # Show all question images
        try:
            question_paths = json.loads(question.question_image_paths or '[]')
            if not question_paths:
                question_paths = [question.question_image_path]
        except (json.JSONDecodeError, TypeError):
            question_paths = [question.question_image_path]
        
        if len(question_paths) == 1:
            st.image(question_paths[0])
        else:
            st.markdown(f"**Question has {len(question_paths)} images:**")
            cols = st.columns(min(3, len(question_paths)))
            for i, q_path in enumerate(question_paths):
                with cols[i % len(cols)]:
                    st.image(q_path, caption=f"Part {i+1}")

    try:
        image_paths = json.loads(progress_data['submission'].original_image_paths or '[]')
    except (json.JSONDecodeError, TypeError):
        image_paths = []

    if not image_paths:
        st.error("This submission has no answer sheet images to crop from.")
        return

    # Simplified page selection - let Streamlit handle widget state
    selected_page = st.number_input(
        f"Select page (1 to {len(image_paths)})",
        min_value=1, max_value=len(image_paths), 
        value=1,  # Default to page 1
        key=f"page_selector_{question_id}"
    )
    page_index = selected_page - 1  # Convert to 0-based indexing
    
    
    img = Image.open(image_paths[page_index])
    cropped_img = st_cropper(img, realtime_update=True, box_color="#FF4B4B", return_type="image", key=f"cropper_{question_id}_{page_index}")

    if cropped_img and st.button("💾 Save Answer Mapping", type="primary"):
        with st.spinner("Saving..."):
            success, message, _ = SubmissionService.create_answer_mapping(
                submission_id=progress_data['submission_id'],
                question_id=question_id,
                cropped_images=[cropped_img],
                student_name=progress_data['student_name'],
                source_page_index=page_index
            )
            if success:
                st.success(message)
                app_state.selected_question_for_mapping = None # Reset selection
                st.rerun()
            else:
                st.error(f"❌ Failed to map answer: {message}")
