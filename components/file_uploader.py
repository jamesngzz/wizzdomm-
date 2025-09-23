# components/file_uploader.py
import streamlit as st
from typing import List, Tuple, Dict, Any
from PIL import Image

from core.config import SUPPORTED_IMAGE_FORMATS, SUPPORTED_FILE_FORMATS, MAX_IMAGE_SIZE_MB, MAX_PDF_SIZE_MB

class FileUploaderComponent:
    """
    Thành phần giao diện có thể tái sử dụng để xử lý tải lên tập tin với xác thực và xem trước.
    Thành phần này tập trung vào hiển thị các widget và trả về dữ liệu đầu vào của người dùng.
    """

    @staticmethod
    def _render_file_previews(uploaded_files: List, preview_columns: int):
        """Hiển thị lưới xem trước tập tin (ảnh và PDF)."""
        st.markdown("**Xem trước tập tin:**")
        cols = st.columns(preview_columns)
        for i, uploaded_file in enumerate(uploaded_files):
            with cols[i % preview_columns]:
                try:
                    if uploaded_file.name.lower().endswith('.pdf'):
                        # PDF preview
                        file_size_mb = uploaded_file.size / (1024 * 1024)
                        st.markdown(f"📄 **{uploaded_file.name}**")
                        st.caption(f"PDF • {file_size_mb:.1f}MB")
                        if file_size_mb > MAX_PDF_SIZE_MB:
                            st.error(f"⚠️ Quá lớn (tối đa {MAX_PDF_SIZE_MB}MB)")
                        else:
                            st.success("✅ Sẵn sàng")
                    else:
                        # Image preview (existing logic)
                        image = Image.open(uploaded_file)
                        st.image(image, caption=uploaded_file.name)
                except Exception as e:
                    st.error(f"Không thể xem trước {uploaded_file.name}: {e}")

    @staticmethod
    def _render_image_previews(uploaded_files: List, preview_columns: int):
        """Legacy method - redirects to new file preview method."""
        FileUploaderComponent._render_file_previews(uploaded_files, preview_columns)

    @staticmethod
    def render_image_uploader(
        label: str,
        help_text: str = None,
        key: str = None,
        accept_pdf: bool = True
    ) -> List:
        """
        Hiển thị widget tải lên tập tin (ảnh + PDF).
        Logic xác thực hiện tại chủ yếu được xử lý bởi lớp dịch vụ.
        """
        if accept_pdf:
            file_types = SUPPORTED_FILE_FORMATS
            if help_text is None:
                help_text = (f"Định dạng hỗ trợ: {', '.join(SUPPORTED_FILE_FORMATS).upper()}. "
                            f"Ảnh: tối đa {MAX_IMAGE_SIZE_MB}MB, PDF: tối đa {MAX_PDF_SIZE_MB}MB.")
        else:
            file_types = SUPPORTED_IMAGE_FORMATS
            if help_text is None:
                help_text = (f"Định dạng hỗ trợ: {', '.join(SUPPORTED_IMAGE_FORMATS).upper()}. "
                            f"Kích thước tối đa: {MAX_IMAGE_SIZE_MB}MB mỗi tập tin.")

        uploaded_files = st.file_uploader(
            label=label,
            type=file_types,
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
        
        st.subheader("📷 Tải lên đề thi")
        uploaded_files = FileUploaderComponent.render_image_uploader(
            label="Tải lên đề thi (ảnh hoặc PDF).*",
            key=f"exam_uploader_{key_suffix}"
        )

        if uploaded_files:
            FileUploaderComponent._render_file_previews(uploaded_files, preview_columns=4)

        return uploaded_files, exam_name, topic, grade_level
