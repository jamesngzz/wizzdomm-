# components/shared_components.py
import streamlit as st
from typing import List, Callable, Any, Optional

def render_selection_box(
    label: str,
    options: List[Any],
    format_func: Callable[[Any], str],
    key: str,
    help_text: str = ""
) -> Optional[Any]:
    """
    Renders a generic, reusable selectbox for choosing an item from a list.

    Args:
        label: The label for the selectbox.
        options: A list of objects to be selected from.
        format_func: A function that takes an object from the list and returns a display string.
        key: A unique key for the Streamlit widget.
        help_text: Optional help text that appears on hover.

    Returns:
        The selected object from the options list, or None if the options list is empty.
    """
    if not options:
        st.warning(f"⚠️ No options available for '{label}'.")
        return None

    # Use range(len(options)) for the options to ensure the widget state is stable
    # even if the underlying objects change. The format_func handles the display.
    selected_index = st.selectbox(
        label=label,
        options=range(len(options)),
        format_func=lambda index: format_func(options[index]),
        key=key,
        help=help_text
    )
    
    return options[selected_index] if selected_index is not None else None

def render_confirmation_dialog(
    item_name: str,
    on_confirm: Callable,
    on_cancel: Callable,
    dialog_key: str,
    warning_text: str = ""
):
    """
    Renders a generic confirmation dialog for destructive actions like deletion.

    Args:
        item_name: The name of the item to be acted upon (e.g., "Question 1a").
        on_confirm: The callback function to execute when the user confirms.
        on_cancel: The callback function to execute when the user cancels.
        dialog_key: A unique base key for the dialog's buttons to avoid conflicts.
        warning_text: Optional additional text to display in the warning.
    """
    with st.container(border=True):
        st.warning(f"⚠️ **Confirm Action**")
        st.markdown(f"Are you sure you want to permanently delete **{item_name}**?")
        
        default_warning = "This action cannot be undone and will remove all associated data, including student answers and grades for this item."
        st.markdown(warning_text if warning_text else default_warning)
        
        col1, col2, _ = st.columns([1, 1, 3])
        with col1:
            if st.button("❌ Confirm Delete", type="primary", key=f"confirm_{dialog_key}"):
                on_confirm()
                # Rerunning is handled by the calling page to allow for toast/success messages
        with col2:
            if st.button("Cancel", key=f"cancel_{dialog_key}"):
                on_cancel()
                st.rerun()