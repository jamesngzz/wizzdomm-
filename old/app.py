# app.py
import streamlit as st
import os
import sys

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.config import APP_TITLE, APP_SUBTITLE, APP_ICON, LAYOUT
from core.state_manager import app_state  # Use the new state manager
from pages import (
    show_create_exam_page,
    show_digitize_exam_page,
    show_submissions_page,
    show_grading_results_page
)

# Configure Streamlit page
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=LAYOUT,
    initial_sidebar_state="expanded"
)

def main():
    """Main application entry point"""
    st.title(f"{APP_ICON} {APP_TITLE}")
    st.caption(APP_SUBTITLE)

    # Define pages configuration in Vietnamese
    PAGES = [
        ("📝 Tạo đề thi", show_create_exam_page),
        ("✂️ Số hóa đề thi", show_digitize_exam_page),
        ("👥 Bài làm học sinh", show_submissions_page),
        ("🎯 Chấm bài & Kết quả", show_grading_results_page)
    ]
    
    page_names = [name for name, _ in PAGES]
    page_functions = {name: func for name, func in PAGES}
    
    # Navigation sidebar in Vietnamese
    with st.sidebar:
        st.header("🗂️ Điều hướng")
        # The current page is now managed by our centralized state manager
        current_index = page_names.index(app_state.page) if app_state.page in page_names else 0

        selected_page = st.radio(
            "Chọn chức năng:",
            page_names,
            index=current_index
        )
        
        # Update state if user selects a different page
        if selected_page != app_state.page:
            app_state.page = selected_page
            # Optional: Add logic here to reset state of the page you are leaving
            st.rerun()
    
    # Route to the selected page based on the state
    page_functions[app_state.page]()

if __name__ == "__main__":
    main()