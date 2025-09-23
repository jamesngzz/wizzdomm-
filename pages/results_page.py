# pages/results_page.py
import streamlit as st
import os
import sys
import json
from PIL import Image
from streamlit_drawable_canvas import st_canvas

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from services.submission_service import SubmissionService
from services.results_service import results_service
from components.shared_components import render_selection_box
from components.canvas_helper import CanvasHelper

def show_results_page():
    """
    Trang xem kết quả tổng thể và tạo báo cáo.
    Bước 2: Canvas tương tác cho phản hồi trực quan.
    """
    st.header("📊 Kết quả & Báo cáo")
    st.markdown("Xem xét kết quả AI và cung cấp phản hồi trực quan bằng cách kéo chú thích lên bài làm.")

    sub_success, _, submissions = SubmissionService.get_all_submissions_with_answers()
    
    if not submissions:
        st.warning("⚠️ Không tìm thấy bài làm đã chấm điểm. Vui lòng chấm điểm bài làm trước.")
        return

    st.subheader("📋 Chọn bài làm để xem xét")
    selected_submission_data = render_selection_box(
        label="Chọn bài làm:",
        options=submissions,
        format_func=lambda s: f"{s['submission'].student_name} - {s['exam_name']} (ID: {s['submission'].id})",
        key="results_submission_selector"
    )

    if not selected_submission_data:
        st.info("Chọn bài làm từ danh sách trên để xem kết quả.")
        return

    st.divider()

    submission_id = selected_submission_data['submission'].id
    results_data = results_service.get_results_for_submission(submission_id)
    
    if not results_data:
        st.error("Không thể tải kết quả cho bài làm này.")
        return
        
    st.header(f"Kết quả cho: {results_data['student_name']}")
    st.caption(f"Đề thi: {results_data['exam_name']}")

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("✍️ Canvas phản hồi trực quan")
        image_paths = results_data['submission_image_paths']
        
        if not image_paths:
            st.warning("Không tìm thấy hình ảnh bài làm cho bài nộp này.")
        else:
            # Initialize page_index at module scope to avoid scoping issues
            page_index = 0
            if len(image_paths) > 1:
                page_selection = st.selectbox(
                    "Chọn trang để chú thích:", 
                    options=[f"Trang {i+1}" for i in range(len(image_paths))],
                    key=f"page_select_{submission_id}"
                )
                page_index = int(page_selection.split(" ")[1]) - 1

            try:
                bg_image = Image.open(image_paths[page_index]).convert("RGBA")
            except FileNotFoundError:
                st.error(f"Không tìm thấy hình ảnh tại đường dẫn: {image_paths[page_index]}")
                return

            # Add circle count control
            circle_count = st.slider("Số hình tròn cần thêm:", min_value=0, max_value=15, value=0, step=1)
            
            initial_drawing = CanvasHelper.generate_initial_drawing(
                graded_items=results_data['graded_items'],
                current_page_index=page_index,
                circle_count=circle_count
            )

            st.info("Kéo và thả các hộp màu vào vị trí đúng trên bài làm.")
            # Scale image to fit container while maintaining aspect ratio
            max_width = 500  # Maximum width for better viewing
            scale_factor = min(max_width / bg_image.width, 1.0)  # Don't upscale
            display_width = int(bg_image.width * scale_factor)
            display_height = int(bg_image.height * scale_factor)
            
            canvas_result = st_canvas(
                fill_color="rgba(255, 165, 0, 0.3)",
                stroke_width=0,
                background_image=bg_image,
                initial_drawing=initial_drawing,
                drawing_mode="transform",
                height=display_height,
                width=display_width,
                key=f"canvas_{submission_id}_{page_index}"
            )

    # Ensure page_index is defined for grading summary (fallback if no images)
    if 'page_index' not in locals():
        page_index = 0
        
    with col2:
        st.subheader("🎯 Tóm tắt chấm điểm")
        graded_items = results_data['graded_items']
        
        # Filter items for current page (supports multi-page items)
        items_for_current_page = []
        for item in graded_items:
            source_page_indices = item.get('source_page_indices', [item.get('source_page_index', 0)])
            if page_index in source_page_indices:
                items_for_current_page.append(item)
        
        if not graded_items:
            st.info("Bài làm này chưa được chấm điểm.")
        elif not items_for_current_page:
            # Fallback: show all items with page indicators when no items found for current page
            st.info(f"Không tìm thấy câu hỏi đã chấm cho trang {page_index + 1}. Hiển thị tất cả câu hỏi với chỉ báo trang:")
            items_to_show = graded_items
        else:
            items_to_show = items_for_current_page
            
        # Replace the current marking card section (lines 128-155) with:
        if 'items_to_show' in locals():
            for item in items_to_show:
                with st.container(border=True):
                    # Show page indicators for multi-page items
                    source_page_indices = item.get('source_page_indices', [item.get('source_page_index', 0)])
                    if len(source_page_indices) > 1:
                        pages_str = ', '.join([str(p + 1) for p in source_page_indices])
                        st.markdown(f"**{item['question_label']}** (trải dài nhiều trang: {pages_str})")
                    elif 'items_for_current_page' in locals() and not items_for_current_page:
                        st.markdown(f"**{item['question_label']}** (từ trang {source_page_indices[0] + 1})")
                    else:
                        st.markdown(f"**{item['question_label']}**")
                    
                    # Main result
                    if item['is_correct']:
                        st.success("**Kết quả: ĐÚNG** ✅")
                    else:
                        st.error("**Kết quả: SAI** ❌")

                    if item['partial_credit']:
                        st.info("ℹ️ Được đề xuất chấm điểm một phần cho câu trả lời này.")
                    
                    # ADD DETAILED EXPLANATIONS HERE (like B4)
                    if not item['is_correct']:
                        # Parse critical and part errors from the grading data
                        critical_errors = []
                        part_errors = []
                        
                        # You'll need to modify results_service.py to include these fields
                        if item.get('critical_errors'):
                            try:
                                critical_errors = json.loads(item['critical_errors'])
                            except (json.JSONDecodeError, TypeError):
                                pass
                        
                        if item.get('part_errors'):
                            try:
                                part_errors = json.loads(item['part_errors'])
                            except (json.JSONDecodeError, TypeError):
                                pass
                        
                        # Display critical errors (red)
                        if critical_errors:
                            with st.container(border=True):
                                st.markdown("**🔴 Lỗi nghiêm trọng (Lỗi chí mạng):**")
                                for error in critical_errors:
                                    st.error(f"**{error.get('description', '')}**")
                                    if error.get('phrases'):
                                        for phrase in error['phrases']:
                                            st.markdown(f"- {phrase}")
                        
                        # Display part errors (yellow/warning)
                        if part_errors:
                            with st.container(border=True):
                                st.markdown("**🟡 Lỗi một phần (Lỗi nhỏ/Không chắc chắn):**")
                                for error in part_errors:
                                    st.warning(f"**{error.get('description', '')}**")
                                    if error.get('phrases'):
                                        for phrase in error['phrases']:
                                            st.markdown(f"- {phrase}")
                        
                        # Fallback to legacy error display
                        if not critical_errors and not part_errors and item['error_description']:
                            with st.container(border=True):
                                st.markdown("**🔍 Phân tích lỗi:**")
                                st.warning(item['error_description'])
                                if item['error_phrases']:
                                    st.markdown("**Các điểm lỗi chính:**")
                                    for phrase in item['error_phrases']:
                                        st.markdown(f"- {phrase}")
        
       