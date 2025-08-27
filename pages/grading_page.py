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
    """Page for grading submissions using Vision AI."""
    st.header("🎯 Grade Student Submissions")
    st.markdown("Select a student's submission to begin AI-powered grading.")

    success, _, submissions_data = SubmissionService.get_all_submissions_with_answers()

    if not submissions_data:
        st.warning("⚠️ No student submissions with mapped answers found.")
        if st.button("➕ Go to Submissions Page"):
            app_state.page = "👥 Student Submissions"
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
    """Renders the main grading dashboard for a selected submission."""
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
        with st.spinner("🤖 Executing batch grading... This may take a while."):
            success, msg, _ = grading_service.grade_submission_batch(submission.id)
            st.toast(msg, icon="✅" if success else "❌")
        app_state.grading_in_progress = False
        st.rerun()

    st.divider()
    st.markdown("### 📝 Individual Question Grading")

    # Display each question's grading card
    for item in items:
        GradingInterfaceComponent.render_question_grading_card(
            submission_item=item,
            question=item.question,
            existing_grading=existing_gradings.get(item.id),
            grade_callback=handle_grade_single,
            delete_callback=handle_delete_question
        )

def handle_grade_single(submission_item, question):
    """Callback to grade a single question."""
    with st.spinner(f"🤖 Grading Question..."):
        success, msg, _ = grading_service.grade_single_question(submission_item.id)
        st.toast(msg, icon="✅" if success else "❌")
    st.rerun()

def handle_regrade_all(submission_id):
    """Callback to re-grade all questions."""
    with st.spinner("🔄 Re-grading all questions..."):
        success, msg, _ = grading_service.grade_submission_batch(submission_id, force_regrade=True)
        st.toast(msg, icon="✅" if success else "❌")
    st.rerun()

def handle_delete_question(question, question_label):
    """Callback to initiate question deletion."""
    app_state.question_to_delete_from_grading = {'id': question.id, 'label': question_label}
    st.rerun()