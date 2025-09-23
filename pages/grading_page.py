# pages/grading_page.py
import streamlit as st
import os
import sys
import time

# Add project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.state_manager import app_state
from services.submission_service import SubmissionService
from services.grading_service import grading_service
from services.question_service import QuestionService
from components.grading_interface import GradingInterfaceComponent
from components.shared_components import render_confirmation_dialog

def show_grading_page():
    """Trang chấm điểm bài làm sử dụng AI thị giác."""
    st.header("🎯 Chấm điểm bài làm học sinh")
    st.markdown("Chọn bài làm của học sinh để bắt đầu chấm điểm bằng AI.")

    success, _, submissions_data = SubmissionService.get_all_submissions_with_answers()

    if not submissions_data:
        st.warning("⚠️ Không tìm thấy bài làm học sinh nào có câu trả lời đã ánh xạ.")
        if st.button("➕ Chuyển đến trang bài làm"):
            app_state.page = "👥 Bài làm học sinh"
            st.rerun()
        return

    # Render the selector and get the selected submission data object
    selected_data, _ = GradingInterfaceComponent.render_submission_selector(
        submissions_data, key="main_submission_selector"
    )

    if not selected_data:
        return

    st.divider()
    
    # --- Delete Confirmation Dialog ---
    if app_state.question_to_delete_from_grading:
        info = app_state.question_to_delete_from_grading
        def confirm_delete():
            success, msg, _ = QuestionService.delete_question(info['id'])
            st.toast(msg, icon="✅" if success else "❌")
            app_state.question_to_delete_from_grading = None
        
        render_confirmation_dialog(
            item_name=info['label'],
            on_confirm=confirm_delete,
            on_cancel=lambda: setattr(app_state, 'question_to_delete_from_grading', None),
            dialog_key=f"delete_grading_q_{info['id']}"
        )
        st.divider()

    # --- Display Grading Interface ---
    display_grading_dashboard(selected_data)


def display_grading_dashboard(submission_data):
    """Hiển thị bảng điều khiển chấm điểm chính cho bài làm được chọn."""
    submission = submission_data['submission']
    items = submission_data['items']
    
    # In a full refactor, this would be part of a single service call
    from database.manager_v2 import db_manager
    gradings = db_manager.get_gradings_by_submission(submission.id)
    existing_gradings = {g.submission_item_id: g for g in gradings}
    
    graded_count = len(existing_gradings)
    total_count = len(items)
    correct_count = sum(1 for g in existing_gradings.values() if g.is_correct)

    # Render UI components for progress and batch controls
    GradingInterfaceComponent.render_progress_tracker(graded_count, total_count, correct_count=correct_count)
    GradingInterfaceComponent.render_batch_controls(
        graded_count=graded_count,
        total_count=total_count,
        grading_in_progress=app_state.grading_in_progress,
        batch_callback=lambda: setattr(app_state, 'grading_in_progress', True),
        regrade_callback=lambda: handle_regrade_all(submission.id)
    )

    # Handle the batch grading process if triggered
    if app_state.grading_in_progress:
        with st.spinner("🤖 Đang thực hiện chấm điểm hàng loạt... Có thể mất một lút."):
            success, msg, _ = grading_service.grade_submission_batch(submission.id)
            st.toast(msg, icon="✅" if success else "❌")
        app_state.grading_in_progress = False
        st.rerun()

    st.divider()
    st.markdown("### 📝 Chấm điểm từng câu hỏi")

    # Display each question's grading card
    for item in items:
        GradingInterfaceComponent.render_question_grading_card(
            submission_item=item,
            question=item.question,
            existing_grading=existing_gradings.get(item.id),
            grade_callback=handle_grade_single,
            delete_callback=handle_delete_question
        )

        # Add clarify re-grading workflow for graded items
        if existing_gradings.get(item.id):
            if st.button("🔄 Chấm lại với lời giải thích", key=f"regrade_btn_{item.id}"):
                app_state.regrade_item_id = item.id
                app_state.regrade_clarify_text = app_state.regrade_clarify_text or ""

            if app_state.regrade_item_id == item.id:
                st.info("Vui lòng nhập Clarify bắt buộc cho lần chấm lại.")
                clarify = st.text_area("Lời giải thích cho lần chấm lại (bắt buộc)",
                                     key=f"clarify_text_{item.id}",
                                     value=app_state.regrade_clarify_text,
                                     help="Ví dụ: Ở bước cuối là y^6, không phải y^8")
                c1, c2 = st.columns([1,1])
                with c1:
                    if st.button("Xác nhận chấm lại", key=f"confirm_regrade_{item.id}"):
                        if not clarify or not clarify.strip():
                            st.error("Lời giải thích là bắt buộc.")
                        else:
                            app_state.regrade_clarify_text = clarify.strip()
                            handle_grade_single_with_clarify(item, item.question, app_state.regrade_clarify_text)
                            app_state.regrade_item_id = None
                            app_state.regrade_clarify_text = ""
                with c2:
                    if st.button("Hủy", key=f"cancel_regrade_{item.id}"):
                        app_state.regrade_item_id = None
                        app_state.regrade_clarify_text = ""

def handle_grade_single(submission_item, question):
    """Hàm xử lý chấm điểm một câu hỏi."""
    with st.spinner(f"🤖 Đang chấm điểm câu hỏi..."):
        success, msg, _ = grading_service.grade_single_question(submission_item.id)
        st.toast(msg, icon="✅" if success else "❌")
    st.rerun()

def handle_grade_single_with_clarify(submission_item, question, clarify: str):
    """Hàm xử lý chấm lại một câu hỏi với lời giải thích của giáo viên."""
    with st.spinner(f"🤖 Đang chấm lại với lời giải thích..."):
        success, msg, _ = grading_service.grade_single_question(submission_item.id, clarify=clarify)
        st.toast(msg, icon="✅" if success else "❌")
    st.rerun()

def handle_regrade_all(submission_id):
    """Hàm xử lý chấm lại tất cả các câu hỏi."""
    with st.spinner("🔄 Đang chấm lại tất cả các câu hỏi..."):
        success, msg, _ = grading_service.grade_submission_batch(submission_id, force_regrade=True)
        st.toast(msg, icon="✅" if success else "❌")
    st.rerun()

def handle_delete_question(question, question_label):
    """Hàm xử lý khởi tạo việc xóa câu hỏi."""
    app_state.question_to_delete_from_grading = {'id': question.id, 'label': question_label}
    st.rerun()