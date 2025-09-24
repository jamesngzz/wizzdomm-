import streamlit as st
import json
import os
import sys
from typing import Dict, Any, Optional, List
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.question_solver_service import question_solver_service
from database.manager_v2 import db_manager
from components.shared_components import render_batch_delete_modal

class SolutionReviewComponent:
    """Component for reviewing and approving AI-generated question solutions."""

    @staticmethod
    def _render_content(content: str, title: str = "") -> None:
        """Render content with LaTeX support (simplified approach)"""
        if title:
            st.markdown(f"**{title}**")

        # Simple approach: st.markdown handles LaTeX automatically
        st.markdown(content)

    @staticmethod
    def render_solution_display(solution_data: Dict[str, Any], question_id: int = None) -> None:
        """
        Display a solution with answer, steps, and points in a formatted way.

        Args:
            solution_data: Dictionary containing solution information
            question_id: Optional question ID for actions
        """
        if not solution_data:
            st.warning("⚠️ Không có dữ liệu lời giải")
            return

        # Header with verification status
        col1, col2 = st.columns([3, 1])

        with col1:
            st.subheader("🧮 Lời Giải AI")

        with col2:
            if solution_data.get('verified', False):
                st.success("✅ Đã duyệt")
            else:
                st.warning("⏳ Chờ duyệt")

        # Display answer with simple approach
        st.markdown("### 📝 **Đáp Án:**")
        answer = solution_data.get('answer', 'Không có đáp án')

        # Simple styled container with LaTeX support
        st.info(f"**{answer}**")

        # Display solution steps with enhanced formatting
        steps = solution_data.get('steps', [])
        if steps:
            st.markdown("### 🔢 **Các Bước Giải:**")

            # Show overview if there are many steps
            if len(steps) > 3:
                with st.expander(f"📋 Tổng quan ({len(steps)} bước)", expanded=False):
                    for i, step in enumerate(steps, 1):
                        st.markdown(f"**Bước {i}:** {step.get('description', f'Bước {i}')} *({step.get('points', 0)} điểm)*")

            total_points = 0
            for i, step in enumerate(steps, 1):
                step_points = step.get('points', 0)
                total_points += step_points
                step_description = step.get('description', f'Bước {i}')
                step_content = step.get('content', 'Không có nội dung')

                with st.expander(f"**Bước {i}** - {step_description} *({step_points} điểm)*", expanded=i <= 2):
                    # Simple content display with LaTeX support
                    SolutionReviewComponent._render_content(step_content, "📋 Nội dung:")

            # Display total points
            expected_total = solution_data.get('total_points', total_points)
            st.markdown(f"### 🎯 **Tổng điểm:** {total_points}/{expected_total}")

        # Display additional info section removed for simplicity

        # Display generation info
        if solution_data.get('generated_at'):
            try:
                generated_time = datetime.fromisoformat(solution_data['generated_at'].replace('Z', '+00:00'))
                st.caption(f"🕒 Được tạo lúc: {generated_time.strftime('%d/%m/%Y %H:%M:%S')}")
            except:
                st.caption(f"🕒 Được tạo lúc: {solution_data.get('generated_at')}")

    @staticmethod
    def render_solution_editor(solution_data: Dict[str, Any], question_id: int) -> Optional[Dict[str, Any]]:
        """
        Render an editable solution form for teacher modifications.

        Args:
            solution_data: Current solution data
            question_id: Question ID for saving

        Returns:
            Updated solution data if changes were made, None otherwise
        """
        st.markdown("### ✏️ **Chỉnh Sửa Lời Giải**")

        with st.form(f"solution_editor_{question_id}"):
            # Edit answer
            new_answer = st.text_area(
                "📝 Đáp án:",
                value=solution_data.get('answer', ''),
                height=80,
                help="Chỉnh sửa đáp án cuối cùng"
            )

            # Edit steps
            steps = solution_data.get('steps', [])
            new_steps = []

            st.markdown("#### 🔢 Các Bước Giải:")

            for i, step in enumerate(steps):
                st.markdown(f"**Bước {i+1}:**")

                col1, col2 = st.columns([3, 1])

                with col1:
                    step_desc = st.text_input(
                        f"Mô tả bước {i+1}:",
                        value=step.get('description', ''),
                        key=f"step_desc_{i}_{question_id}"
                    )

                with col2:
                    step_points = st.number_input(
                        f"Điểm bước {i+1}:",
                        value=float(step.get('points', 0)),
                        min_value=0.0,
                        max_value=10.0,
                        step=0.1,
                        key=f"step_points_{i}_{question_id}"
                    )

                step_content = st.text_area(
                    f"Nội dung bước {i+1}:",
                    value=step.get('content', ''),
                    height=100,
                    key=f"step_content_{i}_{question_id}"
                )

                new_steps.append({
                    'step_number': i + 1,
                    'description': step_desc,
                    'content': step_content,
                    'points': step_points
                })

            # Edit total points
            new_total_points = st.number_input(
                "📊 Tổng điểm:",
                value=float(solution_data.get('total_points', sum(step.get('points', 0) for step in steps))),
                min_value=0.0,
                max_value=20.0,
                step=0.1
            )

            # Submit button
            submitted = st.form_submit_button("💾 Lưu Chỉnh Sửa", type="primary")

            if submitted:
                # Create updated solution data
                updated_solution = {
                    'answer': new_answer,
                    'steps': new_steps,
                    'total_points': new_total_points,
                    'verified': solution_data.get('verified', False),
                    'generated_at': solution_data.get('generated_at')
                }

                # Update database
                try:
                    success = db_manager.update_question_solution(
                        question_id=question_id,
                        solution_answer=updated_solution['answer'],
                        solution_steps=json.dumps(updated_solution['steps'], ensure_ascii=False),
                        solution_points=json.dumps([step['points'] for step in updated_solution['steps']], ensure_ascii=False),
                        solution_verified=updated_solution['verified']
                    )

                    if success:
                        st.success("✅ Đã lưu chỉnh sửa thành công!")
                        return updated_solution
                    else:
                        st.error("❌ Lỗi khi lưu chỉnh sửa")

                except Exception as e:
                    st.error(f"❌ Lỗi: {str(e)}")

        return None

    @staticmethod
    def render_solution_approval(question_id: int, current_verified: bool = False) -> Optional[bool]:
        """
        Render approval/rejection buttons for a solution.

        Args:
            question_id: Question ID
            current_verified: Current verification status

        Returns:
            New verification status if changed, None otherwise
        """
        st.markdown("### 🎯 **Phê Duyệt Lời Giải**")

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            if st.button("✅ Duyệt", type="primary" if not current_verified else "secondary", key=f"approve_{question_id}"):
                success, message = question_solver_service.verify_solution(question_id, True)
                if success:
                    st.success(message)
                    return True
                else:
                    st.error(f"❌ {message}")

        with col2:
            if st.button("❌ Từ chối", type="secondary", key=f"reject_{question_id}"):
                success, message = question_solver_service.verify_solution(question_id, False)
                if success:
                    st.warning(message)
                    return False
                else:
                    st.error(f"❌ {message}")

        with col3:
            if current_verified:
                st.info("🔒 Lời giải đã được duyệt")
            else:
                st.warning("⏳ Đang chờ phê duyệt")

        return None

    @staticmethod
    def render_solution_summary(questions_with_solutions: List[Any]) -> None:
        """
        Render a summary of solutions for multiple questions.

        Args:
            questions_with_solutions: List of question objects (SQLAlchemy or dict) with their solutions
        """
        if not questions_with_solutions:
            st.info("📝 Chưa có câu hỏi nào được giải")
            return

        st.markdown("### 📊 **Tổng Quan Lời Giải**")

        # Summary stats
        total_questions = len(questions_with_solutions)
        verified_count = sum(1 for q in questions_with_solutions if getattr(q, 'solution_verified', False))
        pending_count = total_questions - verified_count

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric("📝 Tổng câu hỏi", total_questions)

        with col2:
            st.metric("✅ Đã duyệt", verified_count)

        with col3:
            st.metric("⏳ Chờ duyệt", pending_count)

        # Progress bar
        if total_questions > 0:
            progress = verified_count / total_questions
            st.progress(progress)
            st.caption(f"Tiến độ duyệt: {verified_count}/{total_questions} ({progress:.1%})")

        # Questions list
        st.markdown("#### 📋 Danh Sách Câu Hỏi:")

        for question in questions_with_solutions:
            question_id = getattr(question, 'id', None)
            order_index = getattr(question, 'order_index', 0)
            part_label = getattr(question, 'part_label', '') or ''
            verified = getattr(question, 'solution_verified', False)

            # Create question label
            if part_label:
                question_label = f"Câu {order_index}{part_label}"
            else:
                question_label = f"Câu {order_index}"

            # Status icon
            status_icon = "✅" if verified else "⏳"

            with st.expander(f"{status_icon} {question_label} (ID: {question_id})"):
                solution_answer = getattr(question, 'solution_answer', None)
                if solution_answer:
                    st.markdown(f"**Đáp án:** {solution_answer}")

                    # Show step count and total points
                    solution_steps = getattr(question, 'solution_steps', None)
                    if solution_steps:
                        try:
                            steps = json.loads(solution_steps)
                            step_count = len(steps)
                            st.markdown(f"**Số bước:** {step_count}")
                        except:
                            pass

                    solution_points = getattr(question, 'solution_points', None)
                    if solution_points:
                        try:
                            points = json.loads(solution_points)
                            total_points = sum(points) if points else 0
                            st.markdown(f"**Tổng điểm:** {total_points}")
                        except:
                            pass

                    # Generation time
                    solution_generated_at = getattr(question, 'solution_generated_at', None)
                    if solution_generated_at:
                        st.caption(f"🕒 Tạo lúc: {solution_generated_at}")
                else:
                    st.warning("Chưa có lời giải")

    @staticmethod
    def render_batch_solution_actions(question_ids: List[int]) -> None:
        """
        Render batch actions for multiple solutions.

        Args:
            question_ids: List of question IDs to act on
        """
        if not question_ids:
            return

        st.markdown("### ⚡ **Thao Tác Hàng Loạt**")

        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("✅ Duyệt tất cả", key="batch_approve_all"):
                success_count = 0
                for question_id in question_ids:
                    success, _ = question_solver_service.verify_solution(question_id, True)
                    if success:
                        success_count += 1

                if success_count > 0:
                    st.success(f"✅ Đã duyệt {success_count}/{len(question_ids)} lời giải")
                else:
                    st.error("❌ Không thể duyệt lời giải nào")

        with col2:
            if st.button("❌ Từ chối tất cả", key="batch_reject_all"):
                success_count = 0
                for question_id in question_ids:
                    success, _ = question_solver_service.verify_solution(question_id, False)
                    if success:
                        success_count += 1

                if success_count > 0:
                    st.warning(f"⚠️ Đã từ chối {success_count}/{len(question_ids)} lời giải")
                else:
                    st.error("❌ Không thể từ chối lời giải nào")

        with col3:
            if st.button("🗑️ Xóa tất cả lời giải", key="batch_clear_all"):
                st.session_state['show_batch_clear_modal'] = True
                st.rerun()

        # Batch Clear Modal
        if st.session_state.get('show_batch_clear_modal', False):
            def confirm_batch_clear():
                success_count = 0
                for question_id in question_ids:
                    success = db_manager.clear_question_solution(question_id)
                    if success:
                        success_count += 1

                if success_count > 0:
                    st.success(f"🗑️ Đã xóa {success_count}/{len(question_ids)} lời giải")
                else:
                    st.error("❌ Không thể xóa lời giải nào")

                st.session_state['show_batch_clear_modal'] = False
                st.rerun()

            def cancel_batch_clear():
                st.session_state['show_batch_clear_modal'] = False
                st.rerun()

            modal_active = render_batch_delete_modal(
                items_count=len(question_ids),
                item_type="AI solutions",
                on_confirm=confirm_batch_clear,
                on_cancel=cancel_batch_clear,
                modal_key="batch_clear_solutions",
                additional_info="This will clear all AI-generated solutions but keep the questions intact. You can regenerate solutions later."
            )

            # Stop rendering rest of component while modal is active
            if modal_active:
                return