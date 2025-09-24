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
    warning_text: str = "",
    item_type: str = "item",
    show_skip_option: bool = True
):
    """
    Renders an enhanced confirmation dialog for destructive actions like deletion.

    Args:
        item_name: The name of the item to be acted upon (e.g., "Question 1a").
        on_confirm: The callback function to execute when the user confirms.
        on_cancel: The callback function to execute when the user cancels.
        dialog_key: A unique base key for the dialog's buttons to avoid conflicts.
        warning_text: Optional additional text to display in the warning.
        item_type: Type of item for skip confirmation grouping (e.g., "question", "exam").
        show_skip_option: Whether to show "don't ask again" option.
    """
    # Check if skip confirmation is enabled for this user
    skip_key = f"skip_delete_confirmation_{item_type}"
    if st.session_state.get(skip_key, False):
        # User has opted to skip confirmations for this type
        if on_confirm:
            on_confirm()
        return

    # Enhanced visual design
    st.error("🚨 **XÁC NHẬN XÓA**")

    with st.container(border=True):
        st.markdown(f"### Bạn có chắc chắn muốn xóa: **{item_name}**?")

        if warning_text:
            st.warning(f"⚠️ **Cảnh báo:** {warning_text}")
        else:
            st.warning("⚠️ **Cảnh báo:** Hành động này không thể hoàn tác và sẽ xóa tất cả dữ liệu liên quan, bao gồm câu trả lời và điểm số của học sinh cho mục này.")

        st.markdown("---")

        # Skip confirmation option
        if show_skip_option:
            skip_future = st.checkbox(
                f"✅ Không hỏi lại khi xóa {item_type}",
                key=f"{dialog_key}_skip_future",
                help=f"Bỏ qua hộp thoại xác nhận khi xóa {item_type} trong phiên này"
            )

        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            st.markdown("**Nhấn một trong hai nút bên phải để tiếp tục:**")

        with col2:
            if st.button("❌ **XÁC NHẬN XÓA**", type="primary", key=f"confirm_{dialog_key}", use_container_width=True):
                # Handle skip future confirmations
                if show_skip_option and st.session_state.get(f"{dialog_key}_skip_future", False):
                    st.session_state[skip_key] = True

                on_confirm()
                # Rerunning is handled by the calling page to allow for toast/success messages

        with col3:
            if st.button("↩️ Hủy", key=f"cancel_{dialog_key}", use_container_width=True):
                on_cancel()

# DEPRECATED: Modal functions disabled - using simple confirmation dialogs instead
# def render_delete_modal(
#     item_name: str,
#     item_type: str = "item",
#     on_confirm: Callable = None,
#     on_cancel: Callable = None,
#     modal_key: str = None,
#     warning_text: str = "",
#     show_skip_option: bool = True
# ) -> bool:
#     """
#     DEPRECATED: Use render_confirmation_dialog instead.
#     Modern modal-based delete confirmation with skip option.
#     """
#     return ModalManager.render_delete_confirmation_modal(
#         item_name=item_name,
#         item_type=item_type,
#         on_confirm=on_confirm,
#         on_cancel=on_cancel,
#         modal_key=modal_key,
#         warning_text=warning_text,
#         show_skip_option=show_skip_option
#     )

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
    Note: Individual deletes use render_confirmation_dialog instead.

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

def clear_skip_confirmations():
    """Clear all skip confirmation preferences for the session"""
    keys_to_remove = [key for key in st.session_state.keys() if key.startswith("skip_delete_confirmation_")]
    for key in keys_to_remove:
        del st.session_state[key]
    st.success("🔄 Đã đặt lại tùy chọn xác nhận xóa!")