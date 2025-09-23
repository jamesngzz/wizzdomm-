# components/shared_components.py
import streamlit as st
from typing import List, Callable, Any, Optional
from .modal_components import ModalManager

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
        st.warning(f"⚠️ **Xác nhận hành động**")
        st.markdown(f"Bạn có chắc chắn muốn xóa vĩnh viễn **{item_name}**?")

        default_warning = "Hành động này không thể hoàn tác và sẽ xóa tất cả dữ liệu liên quan, bao gồm câu trả lời và điểm số của học sinh cho mục này."
        st.markdown(warning_text if warning_text else default_warning)
        
        col1, col2, _ = st.columns([1, 1, 3])
        with col1:
            if st.button("❌ Xác nhận xóa", type="primary", key=f"confirm_{dialog_key}"):
                on_confirm()
                # Rerunning is handled by the calling page to allow for toast/success messages
        with col2:
            if st.button("Hủy", key=f"cancel_{dialog_key}"):
                on_cancel()
                st.rerun()

def render_delete_modal(
    item_name: str,
    item_type: str = "item",
    on_confirm: Callable = None,
    on_cancel: Callable = None,
    modal_key: str = None,
    warning_text: str = "",
    show_skip_option: bool = True
) -> bool:
    """
    Modern modal-based delete confirmation with skip option.

    Args:
        item_name: Name of item to delete (e.g., "Question 1a")
        item_type: Type of item for skip confirmation grouping
        on_confirm: Callback when user confirms deletion
        on_cancel: Callback when user cancels
        modal_key: Unique key for the modal
        warning_text: Additional warning text
        show_skip_option: Whether to show "don't ask again" option

    Returns:
        bool: True if modal is active and showing
    """
    return ModalManager.render_delete_confirmation_modal(
        item_name=item_name,
        item_type=item_type,
        on_confirm=on_confirm,
        on_cancel=on_cancel,
        modal_key=modal_key,
        warning_text=warning_text,
        show_skip_option=show_skip_option
    )

def render_batch_delete_modal(
    items_count: int,
    item_type: str = "items",
    on_confirm: Callable = None,
    on_cancel: Callable = None,
    modal_key: str = None,
    additional_info: str = ""
) -> bool:
    """
    Modal for batch delete operations.

    Args:
        items_count: Number of items to be deleted
        item_type: Type of items being deleted
        on_confirm: Callback when user confirms
        on_cancel: Callback when user cancels
        modal_key: Unique key for the modal
        additional_info: Additional information to display

    Returns:
        bool: True if modal is active
    """
    return ModalManager.render_batch_delete_modal(
        items_count=items_count,
        item_type=item_type,
        on_confirm=on_confirm,
        on_cancel=on_cancel,
        modal_key=modal_key,
        additional_info=additional_info
    )