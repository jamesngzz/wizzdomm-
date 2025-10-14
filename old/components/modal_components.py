# components/modal_components.py
import streamlit as st
from typing import Callable, Optional, Dict, Any
import uuid

class ModalManager:
    """
    Modal manager for creating popup dialogs with overlay in Streamlit.
    Provides better UX than top-of-page confirmation dialogs.
    """

    @staticmethod
    def render_modal_css():
        """Inject CSS styles for modal functionality"""
        st.markdown("""
        <style>
        /* Modal overlay */
        .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0, 0, 0, 0.6);
            z-index: 9999;
            display: flex;
            justify-content: center;
            align-items: center;
            animation: fadeIn 0.3s ease-out;
        }

        /* Modal content box */
        .modal-content {
            background: white;
            padding: 2rem;
            border-radius: 12px;
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
            max-width: 500px;
            min-width: 400px;
            margin: 20px;
            animation: slideIn 0.3s ease-out;
            position: relative;
        }

        /* Dark theme support */
        .dark .modal-content {
            background: var(--background-color);
            color: var(--text-color);
            border: 1px solid var(--border-color);
        }

        /* Modal header */
        .modal-header {
            margin-bottom: 1.5rem;
            padding-bottom: 1rem;
            border-bottom: 2px solid #f0f0f0;
        }

        .modal-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0;
            color: #dc3545;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }

        /* Modal body */
        .modal-body {
            margin-bottom: 1.5rem;
            line-height: 1.6;
        }

        .modal-item-name {
            font-weight: 600;
            color: #dc3545;
            background: #fff5f5;
            padding: 0.3rem 0.6rem;
            border-radius: 6px;
            border-left: 4px solid #dc3545;
        }

        .modal-warning {
            color: #856404;
            background: #fff3cd;
            padding: 1rem;
            border-radius: 6px;
            border-left: 4px solid #ffc107;
            margin: 1rem 0;
        }

        /* Skip confirmation section */
        .skip-confirmation {
            background: #f8f9fa;
            padding: 1rem;
            border-radius: 6px;
            border-left: 4px solid #6c757d;
            margin: 1rem 0;
        }

        /* Modal footer */
        .modal-footer {
            display: flex;
            gap: 0.75rem;
            justify-content: flex-end;
            padding-top: 1rem;
            border-top: 1px solid #f0f0f0;
        }

        /* Animations */
        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideIn {
            from {
                opacity: 0;
                transform: translateY(-50px) scale(0.95);
            }
            to {
                opacity: 1;
                transform: translateY(0) scale(1);
            }
        }

        /* Close on backdrop click hint */
        .modal-overlay::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            cursor: pointer;
        }

        .modal-content {
            cursor: default;
        }

        /* Responsive design */
        @media (max-width: 768px) {
            .modal-content {
                margin: 10px;
                min-width: auto;
                max-width: calc(100vw - 20px);
                padding: 1.5rem;
            }

            .modal-footer {
                flex-direction: column;
            }
        }
        </style>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_delete_confirmation_modal(
        item_name: str,
        item_type: str = "item",
        on_confirm: Callable = None,
        on_cancel: Callable = None,
        modal_key: str = None,
        warning_text: str = "",
        danger_level: str = "high",
        show_skip_option: bool = True,
        custom_confirm_text: str = None
    ) -> bool:
        """
        Render a delete confirmation modal with improved UX.

        Args:
            item_name: Name of item to delete (e.g., "Question 1a")
            item_type: Type of item (e.g., "question", "exam", "submission")
            on_confirm: Callback when user confirms deletion
            on_cancel: Callback when user cancels
            modal_key: Unique key for the modal
            warning_text: Additional warning text
            danger_level: "low", "medium", "high" - affects styling
            show_skip_option: Whether to show "don't ask again" option
            custom_confirm_text: Custom text for confirm button

        Returns:
            bool: True if modal is active and showing
        """
        if not modal_key:
            modal_key = f"delete_modal_{uuid.uuid4().hex[:8]}"

        # CSS injection
        ModalManager.render_modal_css()

        # Check if skip confirmation is enabled for this user
        skip_key = f"skip_delete_confirmation_{item_type}"
        if st.session_state.get(skip_key, False):
            # User has opted to skip confirmations for this type
            if on_confirm:
                on_confirm()
            return False

        # Modal state management
        modal_state_key = f"{modal_key}_active"

        # Danger level styling
        danger_colors = {
            "low": {"color": "#0d6efd", "bg": "#cff4fc"},
            "medium": {"color": "#fd7e14", "bg": "#fff3cd"},
            "high": {"color": "#dc3545", "bg": "#f8d7da"}
        }

        color_scheme = danger_colors.get(danger_level, danger_colors["high"])
        confirm_text = custom_confirm_text or f"🗑️ Xóa {item_name}"

        # Modal HTML content
        modal_html = f"""
        <div class="modal-overlay" id="{modal_key}">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">
                        ⚠️ Xác nhận xóa
                    </h3>
                </div>

                <div class="modal-body">
                    <p>Bạn có chắc chắn muốn xóa vĩnh viễn:</p>
                    <div class="modal-item-name">{item_name}</div>

                    <div class="modal-warning">
                        <strong>⚠️ Cảnh báo:</strong> {warning_text or f'Hành động này không thể hoàn tác. Tất cả dữ liệu liên quan đến {item_type} sẽ bị xóa vĩnh viễn, bao gồm cả câu trả lời và điểm số liên quan.'}
                    </div>
                </div>
            </div>
        </div>
        """

        # Render modal overlay
        st.markdown(modal_html, unsafe_allow_html=True)

        # Modal controls in columns
        col1, col2, col3 = st.columns([2, 1, 1])

        with col1:
            if show_skip_option:
                skip_future = st.checkbox(
                    f"Không hỏi lại khi xóa {item_type}",
                    key=f"{modal_key}_skip_future",
                    help=f"Bỏ qua hộp thoại xác nhận khi xóa {item_type} trong phiên này"
                )
                if skip_future:
                    st.session_state[skip_key] = True

        with col2:
            if st.button("Hủy", key=f"{modal_key}_cancel", type="secondary"):
                if on_cancel:
                    on_cancel()
                return False

        with col3:
            if st.button(confirm_text, key=f"{modal_key}_confirm", type="primary"):
                # Handle skip future confirmations
                if show_skip_option and st.session_state.get(f"{modal_key}_skip_future", False):
                    st.session_state[skip_key] = True

                if on_confirm:
                    on_confirm()
                return False

        return True

    @staticmethod
    def render_batch_delete_modal(
        items_count: int,
        item_type: str = "items",
        on_confirm: Callable = None,
        on_cancel: Callable = None,
        modal_key: str = None,
        additional_info: str = ""
    ) -> bool:
        """
        Render a modal for batch delete operations.

        Args:
            items_count: Number of items to be deleted
            item_type: Type of items (e.g., "solutions", "questions")
            on_confirm: Callback when user confirms
            on_cancel: Callback when user cancels
            modal_key: Unique key for the modal
            additional_info: Additional information to display

        Returns:
            bool: True if modal is active
        """
        if not modal_key:
            modal_key = f"batch_delete_modal_{uuid.uuid4().hex[:8]}"

        ModalManager.render_modal_css()

        # Modal HTML for batch operations in Vietnamese
        modal_html = f"""
        <div class="modal-overlay" id="{modal_key}">
            <div class="modal-content">
                <div class="modal-header">
                    <h3 class="modal-title">
                        🗑️ Xác nhận xóa hàng loạt
                    </h3>
                </div>

                <div class="modal-body">
                    <p>Bạn chuẩn bị xóa <strong>{items_count} {item_type}</strong>.</p>

                    <div class="modal-warning">
                        <strong>⚠️ Đây là thao tác hàng loạt!</strong><br>
                        Hành động này sẽ xóa vĩnh viễn tất cả {item_type} đã chọn và không thể hoàn tác.
                        {f'<br><br>{additional_info}' if additional_info else ''}
                    </div>
                </div>
            </div>
        </div>
        """

        st.markdown(modal_html, unsafe_allow_html=True)

        # Controls in Vietnamese
        col1, col2, col3 = st.columns([2, 1, 1])

        with col2:
            if st.button("Hủy", key=f"{modal_key}_cancel", type="secondary"):
                if on_cancel:
                    on_cancel()
                return False

        with col3:
            if st.button(f"Xóa {items_count} {item_type}", key=f"{modal_key}_confirm", type="primary"):
                if on_confirm:
                    on_confirm()
                return False

        return True

    @staticmethod
    def clear_skip_confirmations():
        """Clear all skip confirmation preferences for the session"""
        keys_to_remove = [key for key in st.session_state.keys() if key.startswith("skip_delete_confirmation_")]
        for key in keys_to_remove:
            del st.session_state[key]
        st.success("🔄 Đã đặt lại tùy chọn xác nhận xóa!")