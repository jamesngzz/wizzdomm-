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
    st.header("📝 Tạo đề thi mới")
    st.markdown("Bắt đầu bằng cách tải lên hình ảnh đề thi và nhập thông tin cơ bản.")

    # Exam creation form
    with st.form("create_exam_form"):
        uploaded_files, exam_name, topic, grade_level = FileUploaderComponent.render_exam_uploader("create_exam")
        submit_button = st.form_submit_button("🚀 Tạo đề thi", type="primary")

        if submit_button:
            # 1. Save images via the ImageService
            img_success, img_message, saved_paths = ImageService.save_uploaded_exam_images(
                uploaded_files, exam_name
            )

            if not img_success:
                st.error(f"❌ Xử lý hình ảnh thất bại: {img_message}")
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
                    st.info("🎯 Bước tiếp theo: Chuyển đến 'Số hóa đề thi' để cắt từng câu hỏi.")
                else:
                    st.error(f"❌ Tạo đề thi thất bại: {create_message}")

    # --- Show existing exams ---
    st.divider()
    st.subheader("📚 Đề thi hiện có")

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
                    display_text = (f"📝 **{exam['name']}** - {exam.get('topic', 'Chưa có')} "
                                    f"({exam['question_count']} câu hỏi)")
                    st.write(display_text)

                with col2:
                    if st.button("📋 Chi tiết", key=f"details_{exam['id']}", help="Xem chi tiết"):
                        # Toggle details view using the centralized state
                        if app_state.selected_exam_details == exam['id']:
                            app_state.selected_exam_details = None
                        else:
                            app_state.selected_exam_details = exam['id']
                        st.rerun()

                # Expanded view for the selected exam
                if app_state.selected_exam_details == exam['id']:
                    with st.container(border=True):
                        st.write(f"**Chủ đề:** {exam.get('topic', 'Chưa có')}")
                        st.write(f"**Khối lớp:** {exam.get('grade_level', 'Chưa có')}")
                        st.write(f"**Câu hỏi đã số hóa:** {exam['question_count']}")
                        st.write(f"**Tạo lúc:** {exam['created_at'].strftime('%Y-%m-%d %H:%M')}")
                        
                        if st.button(f"✂️ Số hóa đề thi này", key=f"digitize_{exam['id']}"):
                            app_state.current_exam_id = exam['id']
                            app_state.page = "✂️ Số hóa đề thi"
                            st.rerun()
        else:
            st.info("Chưa có đề thi nào được tạo. Hãy tạo đề thi đầu tiên ở trên!")

    except Exception as e:
        st.error(f"Có lỗi xảy ra khi hiển thị đề thi: {e}")