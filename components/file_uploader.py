# components/file_uploader.py
import streamlit as st
from typing import List, Tuple, Dict, Any
from PIL import Image

from core.config import SUPPORTED_IMAGE_FORMATS, MAX_IMAGE_SIZE_MB

class FileUploaderComponent:
    """
    Thành phần giao diện có thể tái sử dụng để xử lý tải lên tập tin với xác thực và xem trước.
    Thành phần này tập trung vào hiển thị các widget và trả về dữ liệu đầu vào của người dùng.
    """

    @staticmethod
    def _render_image_previews(uploaded_files: List, preview_columns: int):
        """Hiển thị lưới xem trước hình ảnh."""
        st.markdown("**Xem trước hình ảnh:**")
        cols = st.columns(preview_columns)
        for i, uploaded_file in enumerate(uploaded_files):
            with cols[i % preview_columns]:
                try:
                    image = Image.open(uploaded_file)
                    st.image(image, caption=uploaded_file.name)
                except Exception as e:
                    st.error(f"Không thể xem trước {uploaded_file.name}: {e}")

    @staticmethod
    def render_image_uploader(
        label: str,
        help_text: str = None,
        key: str = None
    ) -> List:
        """
        Hiển thị widget tải lên hình ảnh tổng quát.
        Logic xác thực hiện tại chủ yếu được xử lý bởi lớp dịch vụ.
        """
        if help_text is None:
            help_text = (f"Định dạng hỗ trợ: {', '.join(SUPPORTED_IMAGE_FORMATS).upper()}. "
                         f"Kích thước tối đa: {MAX_IMAGE_SIZE_MB}MB mỗi tập tin.")

        uploaded_files = st.file_uploader(
            label=label,
            type=SUPPORTED_IMAGE_FORMATS,
            accept_multiple_files=True,
            help=help_text,
            key=key
        )
        return uploaded_files or []

    @staticmethod
    def render_exam_uploader(key_suffix: str) -> Tuple[List, str, str, str]:
        """
        Hiển thị giao diện cụ thể cho việc tạo đề thi, bao gồm các trường nhập metadata.

        Trả về:
            Một tuple chứa (uploaded_files, exam_name, topic, grade_level).
        """
        st.subheader("📋 Thông tin đề thi")
        col1, col2 = st.columns(2)
        with col1:
            exam_name = st.text_input(
                "Tên đề thi*",
                placeholder="vd: Kiểm tra giữa kỳ I",
                key=f"exam_name_{key_suffix}"
            )
            topic = st.text_input(
                "Chủ đề*",
                placeholder="vd: Phương trình bậc hai, Hình học",
                key=f"topic_{key_suffix}"
            )
        with col2:
            grade_level = st.selectbox(
                "Khối lớp*",
                options=[f"Lớp {i}" for i in range(6, 13)],
                index=4,  # Mặc định là Lớp 10
                key=f"grade_{key_suffix}"
            )
        
        st.subheader("📷 Tải lên hình ảnh đề thi")
        uploaded_files = FileUploaderComponent.render_image_uploader(
            label="Tải lên một hoặc nhiều trang của đề thi.*",
            key=f"exam_uploader_{key_suffix}"
        )

        if uploaded_files:
            FileUploaderComponent._render_image_previews(uploaded_files, preview_columns=4)

        return uploaded_files, exam_name, topic, grade_level
