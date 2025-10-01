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
    """Trang quản lý bài làm học sinh và ánh xạ câu trả lời."""
    
    # Nếu đang ở chế độ ánh xạ, chỉ hiển thị giao diện ánh xạ để tập trung
    if app_state.mapping_mode and app_state.current_submission_id:
        show_answer_mapping_interface()
        return

    # --- Giao diện chính khi không ở chế độ ánh xạ ---
    st.header("👥 Bài làm học sinh")
    st.markdown("Chọn một đề thi để xem các bài làm hiện tại hoặc tạo bài làm mới.")

    # --- 1. Exam Selection (Bước chọn kỳ thi) ---
    exam_success, _, exams = ExamService.get_exam_list()
    if not exams:
        st.warning("⚠️ Không tìm thấy đề thi nào. Vui lòng tạo đề thi trước.")
        return

    selected_exam = render_selection_box(
        label="Chọn đề thi:",
        options=exams,
        format_func=lambda e: f"{e['name']} - {e.get('topic', 'Chưa có')} (ID: {e['id']})",
        key="submission_exam_selector"
    )
    if not selected_exam:
        st.info("Vui lòng chọn đề thi để tiếp tục.")
        return

    selected_exam_id = selected_exam['id']

    st.divider()

    # --- 2. Display Existing Submissions for the selected exam ---
    st.subheader(f"📚 Các bài làm hiện có cho '{selected_exam['name']}'")
    
    # Lấy các submission đã lọc theo exam_id
    submissions_for_exam = db_manager.list_submissions_by_exam(selected_exam_id)

    if not submissions_for_exam:
        st.info("Chưa có bài làm nào được tạo cho đề thi này. Sử dụng biểu mẫu bên dưới để tạo một bài làm.")
    else:
        for sub_info in submissions_for_exam:
            sub_id = sub_info['id']
            # Lấy thông tin tiến độ
            #_, _, progress = SubmissionService.get_submission_progress(sub_id)
            
            col1, col2, col3, col4 = st.columns([2, 1.5, 1, 1])
            with col1:
                st.markdown(f"**🧑‍🎓 {sub_info['student_name']}**")
                st.caption(f"Nộp lúc: {sub_info['created_at'].strftime('%Y-%m-%d %H:%M')}")
            with col2:
                # Hiển thị số lượng item đã ánh xạ là đủ ở đây
                item_count = sub_info['item_count']
                st.markdown(f"**Ánh xạ:** {item_count}")

            with col3:
                if st.button("📝 Ánh xạ", key=f"map_{sub_id}", help="Tiếp tục ánh xạ câu trả lời"):
                    app_state.current_submission_id = sub_id
                    app_state.mapping_mode = True
                    st.rerun()

            with col4:
                if st.button("🎯 Chấm bài", key=f"grade_{sub_id}", help="Chấm bài và xem kết quả"):
                    # Set state để navigate đến grading results page với submission này
                    app_state.selected_submission_for_grading = sub_id
                    app_state.page = "🎯 Chấm bài & Kết quả"
                    st.rerun()

    st.divider()

    # --- 3. Create New Submission Section (Form tạo mới) ---
    with st.expander("📝 Tạo bài làm mới cho đề thi này", expanded=not submissions_for_exam):
        student_name = st.text_input("Tên học sinh*", placeholder="Nguyễn Văn A", key="new_student_name")
        uploaded_files = st.file_uploader(
            "Tải lên bài làm*",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            key="new_submission_uploader"
        )
        
        # Preview uploaded images
        if uploaded_files:
            st.markdown("**Xem trước hình ảnh:**")
            cols = st.columns(4)
            for i, uploaded_file in enumerate(uploaded_files):
                with cols[i % 4]:
                    try:
                        image = Image.open(uploaded_file)
                        st.image(image, caption=uploaded_file.name)
                    except Exception as e:
                        st.error(f"Không thể xem trước {uploaded_file.name}: {e}")

        if st.button("🚀 Tạo bài làm", type="primary"):
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
                st.error(f"❌ Tạo bài làm thất bại: {message}")

def show_answer_mapping_interface():
    """Hiển thị giao diện ánh xạ câu trả lời cho bài làm được lưu trong trạng thái ứng dụng."""
    sub_id = app_state.current_submission_id
    success, msg, progress = SubmissionService.get_submission_progress(sub_id)

    if not success or not progress:
        st.error(f"Lỗi khi tải dữ liệu bài làm: {msg}")
        # Nút để thoát khỏi chế độ ánh xạ nếu có lỗi
        if st.button("🔙 Quay lại"):
            app_state.mapping_mode = False
            app_state.current_submission_id = None
            st.rerun()
        return
    
    st.header("✂️ Ánh xạ câu trả lời")
    st.info(f"**Ánh xạ cho:** {progress['student_name']} | "
            f"**Đề thi:** {progress['submission'].exam.name} | "
            f"**Tiến độ:** {progress['mapped_answers']}/{progress['total_questions']} câu hỏi đã ánh xạ.")

    if st.button("✅ Hoàn thành ánh xạ & quay lại danh sách"):
        app_state.mapping_mode = False
        app_state.current_submission_id = None
        st.rerun()

    q_success, _, questions = QuestionService.get_questions_by_exam(progress['submission'].exam_id)
    mapped_ids = {item.question_id for item in progress['items']}
    
    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown("**Câu hỏi cần ánh xạ**")
        for q in questions:
            is_mapped = q.id in mapped_ids
            status_icon = "✅" if is_mapped else "⏳"
            label = format_question_label(q.order_index, q.part_label)
            # Dùng st.radio để tự động quản lý trạng thái câu hỏi được chọn
            if st.button(f"{status_icon} {label}", key=f"map_btn_{q.id}", use_container_width=True):
                # Reset states when switching questions
                st.session_state['cropped_img_ready'] = False
                st.session_state['save_triggered'] = False
                # Reset page selector for new question
                session_key = f"current_selected_page_{q.id}"
                if session_key in st.session_state:
                    st.session_state[session_key] = 1
                app_state.selected_question_for_mapping = q.id
                st.rerun() # Rerun để cập nhật cột bên phải

        # Add save button below the question list
        st.markdown("---")

        # Check if cropped image is ready
        button_enabled = (app_state.selected_question_for_mapping and
                         st.session_state.get('cropped_img_ready', False))

        if button_enabled:
            if st.button("💾 Lưu ánh xạ câu trả lời", type="primary", use_container_width=True, key="save_mapping_left"):
                st.session_state['save_triggered'] = True
                st.rerun()
        else:
            st.button("💾 Lưu ánh xạ câu trả lời", type="primary", use_container_width=True, key="save_mapping_left", disabled=True)
            if not app_state.selected_question_for_mapping:
                st.caption("👈 Chọn câu hỏi để ánh xạ")
            elif not st.session_state.get('cropped_img_ready', False):
                st.caption("✂️ Crop ảnh để kích hoạt nút lưu")

    with col2:
        st.markdown("**Cắt câu trả lời học sinh**")
        if app_state.selected_question_for_mapping:
            display_answer_cropping_ui(progress)
        else:
            st.info("👈 Chọn một câu hỏi ở bên trái để ánh xạ câu trả lời.")

def display_answer_cropping_ui(progress_data):
    """Hiển thị giao diện cắt câu trả lời cho câu hỏi được chọn."""
    question_id = app_state.selected_question_for_mapping

    # ✅ XỬ LÝ SAVE NGAY TỪ ĐẦU - TRƯỚC KHI RENDER UI
    if st.session_state.get('save_triggered', False) and st.session_state.get('cropped_img_ready', False):
        with st.spinner("Đang lưu..."):
            success, message, _ = SubmissionService.create_answer_mapping(
                submission_id=progress_data['submission_id'],
                question_id=question_id,
                cropped_images=[st.session_state['current_cropped_img']],
                student_name=progress_data['student_name'],
                source_page_index=st.session_state['current_page_index'],
                bbox_coordinates=st.session_state['current_bbox_coords'],
                original_dimensions=st.session_state['current_img_dimensions']
            )
            if success:
                st.success(message)
                app_state.selected_question_for_mapping = None
                # Clear session states
                st.session_state['save_triggered'] = False
                st.session_state['cropped_img_ready'] = False
                # Reset page selector for this question
                session_key = f"current_selected_page_{question_id}"
                st.session_state.pop(session_key, None)
                st.rerun()
            else:
                st.error(f"❌ Ánh xạ câu trả lời thất bại: {message}")
                st.session_state['save_triggered'] = False
        return  # Return ngay sau khi lưu - không render UI nữa

    success, msg, question = QuestionService.get_question_by_id(question_id)

    if not success or not question:
        st.error(f"Không thể tải dữ liệu câu hỏi: {msg}")
        return

    st.success(f"Ánh xạ câu trả lời cho: **{format_question_label(question.order_index, question.part_label)}**")

    # Display existing cropped images for this question
    existing_items = db_manager.get_submission_items_by_question(
        submission_id=progress_data['submission_id'],
        question_id=question_id
    )

    if existing_items:
        with st.expander(f"📸 Hình ảnh đã cắt cho câu này ({len(existing_items)} ảnh)", expanded=True):
            cols = st.columns(min(3, len(existing_items)))
            for i, item in enumerate(existing_items):
                with cols[i % len(cols)]:
                    try:
                        # Display primary cropped image
                        if item.answer_image_path and os.path.exists(item.answer_image_path):
                            st.image(item.answer_image_path, caption=f"Ảnh cắt {i+1}", width=150)

                        # Display additional cropped images if any
                        if item.answer_image_paths:
                            try:
                                additional_paths = json.loads(item.answer_image_paths)
                                for j, add_path in enumerate(additional_paths):
                                    if os.path.exists(add_path):
                                        st.image(add_path, caption=f"Ảnh {i+1}.{j+1}", width=120)
                            except (json.JSONDecodeError, TypeError):
                                pass

                        # Show source page info
                        if hasattr(item, 'source_page_index') and item.source_page_index:
                            st.caption(f"📄 Trang: {item.source_page_index}")

                        # Add delete button for this cropped image
                        if st.button("🗑️", key=f"del_crop_{item.id}", help="Xóa ảnh cắt này"):
                            success = db_manager.delete_submission_item(item.id)
                            if success:
                                st.success("✅ Đã xóa ảnh cắt!")
                                st.rerun()
                            else:
                                st.error("❌ Lỗi khi xóa ảnh cắt")

                    except Exception as e:
                        st.error(f"Lỗi hiển thị ảnh: {e}")

    with st.expander("Hiển thị câu hỏi tham khảo"):
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
            st.markdown(f"**Câu hỏi có {len(question_paths)} hình ảnh:**")
            cols = st.columns(min(3, len(question_paths)))
            for i, q_path in enumerate(question_paths):
                with cols[i % len(cols)]:
                    st.image(q_path, caption=f"Phần {i+1}")

    try:
        image_paths = json.loads(progress_data['submission'].original_image_paths or '[]')
    except (json.JSONDecodeError, TypeError):
        image_paths = []

    if not image_paths:
        st.error("Bài làm này không có hình ảnh bài làm nào để cắt.")
        return

    # Initialize session state for page selector to persist across reruns
    session_key = f"current_selected_page_{question_id}"
    widget_key = f"page_selector_{question_id}"

    if session_key not in st.session_state:
        st.session_state[session_key] = 1

    # Get current value from widget if exists, otherwise use session state
    if widget_key in st.session_state:
        current_page_value = st.session_state[widget_key]
    else:
        current_page_value = st.session_state[session_key]

    # Simple page selection with persisted value
    selected_page = st.number_input(
        f"Chọn trang (1 đến {len(image_paths)})",
        min_value=1, max_value=len(image_paths),
        value=current_page_value,  # Use persisted value
        key=widget_key
    )

    # Update session state when page changes
    st.session_state[session_key] = selected_page

    page_index = selected_page - 1  # Convert to 0-based indexing

    img = Image.open(image_paths[page_index])

    # Simple cropping instructions
    st.markdown("**Bước 1: Chọn vùng cần cắt**")
    bbox_coords = st_cropper(img, realtime_update=True, box_color="#FF4B4B", return_type="box", key=f"cropper_{question_id}_{page_index}")

    # If we have bbox coordinates, crop the image manually for preview
    cropped_img = None
    if bbox_coords and all(k in bbox_coords for k in ['left', 'top', 'width', 'height']):
        try:
            # Manually crop the image using bbox coordinates
            left = int(bbox_coords['left'])
            top = int(bbox_coords['top'])
            width = int(bbox_coords['width'])
            height = int(bbox_coords['height'])

            # Crop the image
            cropped_img = img.crop((left, top, left + width, top + height))

            st.markdown("**Bước 2: Xem trước vùng đã cắt**")
            st.image(cropped_img, caption="Vùng đã cắt", width=300)

        except Exception as e:
            st.error(f"Lỗi khi cắt ảnh: {e}")
            cropped_img = None

    # Store cropped image and data in session state for left button to use
    if cropped_img:
        st.session_state['current_cropped_img'] = cropped_img
        st.session_state['current_bbox_coords'] = bbox_coords
        st.session_state['current_page_index'] = page_index
        st.session_state['current_img_dimensions'] = {"width": img.width, "height": img.height}
        st.session_state['cropped_img_ready'] = True
    else:
        st.session_state['cropped_img_ready'] = False
