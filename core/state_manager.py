# core/state_manager.py
import streamlit as st
from typing import Dict, Any

class AppState:
    """
    A centralized class to manage the application's session state.
    This revised version is more robust and avoids common pitfalls
    with __setattr__.
    """
    def __init__(self):
        # The key idea is to store the state dictionary within the object's
        # own __dict__, making it a normal attribute. This avoids overriding
        # __setattr__ in a fragile way. We point this attribute to a dict
        # within st.session_state to achieve persistence.
        
        # Ensure the session state dictionary exists
        if 'app_state_dict' not in st.session_state:
            st.session_state.app_state_dict = self._get_initial_state()
            
        # Point this instance's __dict__ to the session state dict.
        # This is the magic that makes the instance stateful across reruns.
        self.__dict__ = st.session_state.app_state_dict

    def _get_initial_state(self) -> Dict[str, Any]:
        """Defines the initial state of the application."""
        return {
            "page": "📝 Create Exam",
            "current_exam_id": None,
            "current_submission_id": None,
            "selected_exam_details": None,
            "question_to_delete": None,
            "selected_question_for_mapping": None,
            "mapping_mode": False,
            "grading_in_progress": False,
            "last_saved_question": None,
            "last_submission_created": None,
            "question_to_delete_from_grading": None,
            "regrade_item_id": None,
            "regrade_clarify_text": "",
        }

    # With the new __init__, we no longer need to override __getattr__ and __setattr__
    # Python's default behavior will now work directly on the dictionary
    # we assigned to self.__dict__.

    def reset_page_state(self, page_keys: list):
        """Resets specific keys in the state, useful when navigating away from a page."""
        initial_state = self._get_initial_state()
        for key in page_keys:
            if key in self.__dict__:
                self.__dict__[key] = initial_state.get(key)

    def reset(self):
        """Resets the entire application state to its initial values."""
        st.session_state.app_state_dict = self._get_initial_state()
        self.__dict__ = st.session_state.app_state_dict

# Create a single global instance to be used across the application
app_state = AppState()