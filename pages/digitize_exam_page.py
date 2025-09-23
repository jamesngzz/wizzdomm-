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
from services.question_solver_service import question_solver_service
from components.shared_components import render_selection_box, render_confirmation_dialog, render_delete_modal
from components.solution_review import SolutionReviewComponent
from core.utils import format_question_label
import asyncio

def show_digitize_exam_page():
    """Page for digitizing exams, using shared components for selection and deletion."""
    st.header("✂️ Số hóa câu hỏi đề thi")
    st.markdown("Cắt từng câu hỏi riêng biệt từ đề thi để tạo ngân hàng câu hỏi có cấu trúc.")

    # --- Exam Selection ---
    st.subheader("📚 Chọn đề thi để số hóa")

    success, _, exams = ExamService.get_exam_list()
    if not exams:
        st.warning("⚠️ Không tìm thấy đề thi nào. Vui lòng tạo đề thi trước.")
        if st.button("➕ Tạo đề thi mới"):
            app_state.page = "📝 Tạo đề thi"
            st.rerun()
        return

    selected_exam = render_selection_box(
        label="Chọn đề thi để số hóa:",
        options=exams,
        format_func=lambda exam: f"{exam['name']} - {exam.get('topic', 'Chưa có')} (ID: {exam['id']})",
        key="digitize_exam_selector"
    )

    if not selected_exam:
        return
        
    app_state.current_exam_id = selected_exam['id']

    # --- Delete Confirmation Modal Logic ---
    if app_state.question_to_delete:
        question_info = app_state.question_to_delete

        def confirm_delete():
            success, msg, _ = QuestionService.delete_question(question_info['id'])
            st.toast(msg, icon="✅" if success else "❌")
            app_state.question_to_delete = None
            st.rerun()

        def cancel_delete():
            app_state.question_to_delete = None
            st.rerun()

        # Use new modal instead of old dialog
        modal_active = render_delete_modal(
            item_name=question_info['label'],
            item_type="question",
            on_confirm=confirm_delete,
            on_cancel=cancel_delete,
            modal_key=f"delete_q_{question_info['id']}",
            warning_text="Thao tác này sẽ xóa vĩnh viễn câu hỏi và tất cả câu trả lời cùng điểm số của học sinh liên quan."
        )

        # Stop rendering rest of page while modal is active
        if modal_active:
            return

    # --- Display Existing Questions ---
    success, _, questions = QuestionService.get_questions_by_exam(app_state.current_exam_id)
    if questions:
        with st.expander(f"📋 Xem câu hỏi hiện có ({len(questions)})"):
            for q in questions:
                label = format_question_label(q.order_index, q.part_label)
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{label}**")
                with col2:
                    st.image(q.question_image_path, width=100)
                with col3:
                    if st.button("🗑️ Xóa", key=f"delete_btn_{q.id}", help=f"Xóa {label}"):
                        app_state.question_to_delete = {'id': q.id, 'label': label}
                        st.rerun()
    st.divider()

    # --- Cropping Interface ---
    display_cropping_interface()

def display_cropping_interface():
    """Renders the main image cropping UI."""
    exam_details = ExamService.get_exam_details(app_state.current_exam_id)[2]
    if not exam_details or not exam_details.original_image_paths:
        st.warning("Đề thi này không có hình ảnh nào để số hóa.")
        return

    try:
        image_paths = json.loads(exam_details.original_image_paths or '[]')
    except (json.JSONDecodeError, TypeError):
        image_paths = []

    if not image_paths:
        st.error("Không tìm thấy hình ảnh nào cho đề thi này.")
        return
    
    # Page navigation for multi-page exams
    page_index = st.number_input(
        f"Chọn trang (1 đến {len(image_paths)})",
        min_value=1, max_value=len(image_paths), value=1,
        help="Chọn trang nào của đề thi để cắt câu hỏi."
    ) - 1

    current_image_path = image_paths[page_index]
    if not os.path.exists(current_image_path):
        st.error(f"Không tìm thấy hình ảnh: {current_image_path}")
        return

    img = Image.open(current_image_path)
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**🎯 Cắt vùng câu hỏi:**")
        cropped_img = st_cropper(img, realtime_update=True, box_color="#0066CC", return_type="image")

    with col2:
        st.markdown("**📝 Chi tiết câu hỏi:**")
        if cropped_img:
            st.image(cropped_img, caption="Xem trước vùng đã cắt")
        
        with st.form("question_form"):
            question_label = st.text_input("Nhãn câu hỏi*", placeholder="vd: 1a, 2b, 3")
            submitted = st.form_submit_button("💾 Lưu câu hỏi", type="primary")

            if submitted:
                if not question_label.strip():
                    st.error("Nhãn câu hỏi không được để trống.")
                elif cropped_img:
                    with st.spinner("Đang lưu câu hỏi..."):
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

    # --- Solution Generation Section ---
    st.divider()
    st.subheader("🧮 Giải câu hỏi bằng AI")

    # Get current questions for this exam
    success, _, exam_questions = QuestionService.get_questions_by_exam(app_state.current_exam_id)

    if not exam_questions:
        st.info("📝 Chưa có câu hỏi nào được tạo. Hãy cắt các câu hỏi trước.")
        return

    # Filter questions that don't have solutions yet
    questions_without_solutions = [q for q in exam_questions if not q.solution_answer]
    questions_with_solutions = [q for q in exam_questions if q.solution_answer]

    # Summary
    total_questions = len(exam_questions)
    solved_questions = len(questions_with_solutions)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📊 Tổng câu hỏi", total_questions)
    with col2:
        st.metric("✅ Đã giải", solved_questions)
    with col3:
        st.metric("⏳ Chưa giải", len(questions_without_solutions))

    # Progress bar
    if total_questions > 0:
        progress = solved_questions / total_questions
        st.progress(progress)
        st.caption(f"Tiến độ giải toán: {solved_questions}/{total_questions} ({progress:.1%})")

    # Batch solution generation
    if questions_without_solutions:
        st.markdown("### 🚀 Tạo lời giải hàng loạt")

        col1, col2 = st.columns([2, 1])

        with col1:
            st.info(f"🎯 Có {len(questions_without_solutions)} câu hỏi chưa được giải")

        with col2:
            if st.button("🧮 Giải Tất Cả", type="primary", key="solve_all_questions"):
                question_ids = [q.id for q in questions_without_solutions]

                with st.spinner(f"Đang giải {len(question_ids)} câu hỏi bằng AI..."):
                    # Run async batch solving
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        success, message, results = loop.run_until_complete(
                            question_solver_service.solve_questions_batch(question_ids)
                        )
                        loop.close()

                        if success:
                            st.success(f"✅ {message}")
                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")

                            # Show detailed results if available
                            if results and results.get('details'):
                                with st.expander("📝 Chi tiết lỗi"):
                                    for detail in results['details']:
                                        status = detail['status']
                                        if status == 'success':
                                            st.success(f"✅ Câu {detail['question_id']}: {detail['message']}")
                                        else:
                                            st.error(f"❌ Câu {detail['question_id']}: {detail['message']}")

                    except Exception as e:
                        st.error(f"❌ Lỗi trong quá trình giải: {str(e)}")

    # Solution review section
    if questions_with_solutions:
        st.markdown("### 📋 Xem và duyệt lời giải")

        # Show solution summary
        SolutionReviewComponent.render_solution_summary(questions_with_solutions)

        # Batch actions for solutions
        verified_solutions = [q for q in questions_with_solutions if q.solution_verified]
        unverified_solutions = [q for q in questions_with_solutions if not q.solution_verified]

        if unverified_solutions:
            st.markdown("#### ⚡ Thao tác hàng loạt")
            unverified_ids = [q.id for q in unverified_solutions]
            SolutionReviewComponent.render_batch_solution_actions(unverified_ids)

        # Individual solution review
        st.markdown("#### 🔍 Xem chi tiết lời giải")

        selected_question = st.selectbox(
            "Chọn câu hỏi để xem lời giải:",
            options=questions_with_solutions,
            format_func=lambda q: f"Câu {q.order_index}{q.part_label or ''} - {'✅ Đã duyệt' if q.solution_verified else '⏳ Chờ duyệt'}",
            key="solution_review_selector"
        )

        if selected_question:
            question_id = selected_question.id

            # Get full solution data
            success, message, solution_data = question_solver_service.get_question_solution(question_id)

            if success and solution_data:
                # Tabs for different views
                tab1, tab2, tab3 = st.tabs(["👀 Xem lời giải", "✏️ Chỉnh sửa", "🎯 Phê duyệt"])

                with tab1:
                    SolutionReviewComponent.render_solution_display(solution_data, question_id)

                with tab2:
                    updated_solution = SolutionReviewComponent.render_solution_editor(solution_data, question_id)
                    if updated_solution:
                        st.rerun()

                with tab3:
                    new_verification = SolutionReviewComponent.render_solution_approval(
                        question_id, solution_data.get('verified', False)
                    )
                    if new_verification is not None:
                        time.sleep(1)
                        st.rerun()
            else:
                st.error(f"❌ Không thể tải lời giải: {message}")

    # Individual question solving
    if questions_without_solutions:
        st.markdown("### 🎯 Giải từng câu hỏi")

        selected_unsolved = st.selectbox(
            "Chọn câu hỏi để giải:",
            options=questions_without_solutions,
            format_func=lambda q: f"Câu {q.order_index}{q.part_label or ''}",
            key="individual_solve_selector"
        )

        if selected_unsolved:
            question_id = selected_unsolved.id

            if st.button(f"🧮 Giải câu {selected_unsolved.order_index}{selected_unsolved.part_label or ''}", key=f"solve_individual_{question_id}"):
                with st.spinner("Đang giải câu hỏi bằng AI..."):
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        success, message, solution_data = loop.run_until_complete(
                            question_solver_service.solve_single_question(question_id)
                        )
                        loop.close()

                        if success:
                            st.success(f"✅ {message}")

                            # Show the generated solution immediately
                            if solution_data:
                                st.markdown("#### 📄 Lời giải vừa tạo:")
                                SolutionReviewComponent.render_solution_display(solution_data, question_id)

                            st.balloons()
                            time.sleep(2)
                            st.rerun()
                        else:
                            st.error(f"❌ {message}")

                    except Exception as e:
                        st.error(f"❌ Lỗi trong quá trình giải: {str(e)}")
