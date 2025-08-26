import streamlit as st
import os
import sys
import json
import time
from PIL import Image
from streamlit_cropper import st_cropper

# Add the project root to Python path so we can import our modules
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from core.config import APP_TITLE, APP_ICON, LAYOUT
from core.utils import format_question_label, parse_question_label, save_cropped_image, save_uploaded_image, validate_image_file, save_multiple_cropped_images
from database.manager_v2 import db_manager
from core.grading_service_v2 import get_grading_service, GradingResult

# Configure Streamlit page
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=APP_ICON,
    layout=LAYOUT
)

def main():
    """Main application entry point"""
    st.title(f"{APP_ICON} {APP_TITLE}")
    
    # Initialize session state for page navigation
    if 'page' not in st.session_state:
        st.session_state.page = "📝 Create Exam"
    
    # Navigation sidebar
    with st.sidebar:
        st.header("🗂️ Navigation")
        page = st.radio(
            "Choose a section:",
            [
                "📝 Create Exam",
                "✂️ Digitize Exam", 
                "👥 Student Submissions",
                "🎯 Grade Submissions",
                "📊 Results & Reports"
            ],
            index=[
                "📝 Create Exam",
                "✂️ Digitize Exam", 
                "👥 Student Submissions",
                "🎯 Grade Submissions",
                "📊 Results & Reports"
            ].index(st.session_state.page) if st.session_state.page in [
                "📝 Create Exam",
                "✂️ Digitize Exam", 
                "👥 Student Submissions",
                "🎯 Grade Submissions",
                "📊 Results & Reports"
            ] else 0
        )
        
        # Update session state if user selects different page
        st.session_state.page = page
    
    # Route to different pages based on selection
    if st.session_state.page == "📝 Create Exam":
        show_create_exam_page()
    elif st.session_state.page == "✂️ Digitize Exam":
        show_digitize_exam_page()
    elif st.session_state.page == "👥 Student Submissions":
        show_submissions_page()
    elif st.session_state.page == "🎯 Grade Submissions":
        show_grading_page()
    elif st.session_state.page == "📊 Results & Reports":
        show_results_page()


def show_create_exam_page():
    """Page for creating new exams"""
    st.header("📝 Create New Exam")
    st.markdown("Start by uploading exam paper images and entering basic information.")
    
    # Initialize session state
    if 'exam_created' not in st.session_state:
        st.session_state.exam_created = False
    if 'current_exam_id' not in st.session_state:
        st.session_state.current_exam_id = None
    
    # Exam creation form
    with st.form("create_exam_form"):
        st.subheader("📋 Exam Information")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            exam_name = st.text_input(
                "Exam Name *", 
                placeholder="e.g., Kiểm tra giữa kỳ I",
                help="Enter a descriptive name for this exam"
            )
        
        with col2:
            topic = st.text_input(
                "Topic *",
                placeholder="e.g., Phương trình bậc 2, Hình học, Đạo hàm",
                help="Enter the topic of this exam"
            )
        
        with col3:
            grade_level = st.selectbox(
                "Grade Level *",
                options=[f"Grade {i}" for i in range(6, 13)],
                index=3,
                help="Select the grade level for this exam"
            )
        
        st.subheader("📷 Upload Exam Images")
        uploaded_files = st.file_uploader(
            "Upload exam paper images",
            type=["png", "jpg", "jpeg"],
            accept_multiple_files=True,
            help="You can upload multiple pages of the exam. Supported formats: PNG, JPG, JPEG"
        )
        
        # Preview uploaded images
        if uploaded_files:
            st.write(f"**{len(uploaded_files)} image(s) selected:**")
            cols = st.columns(min(len(uploaded_files), 4))
            for i, uploaded_file in enumerate(uploaded_files):
                with cols[i % 4]:
                    image = Image.open(uploaded_file)
                    st.image(image, caption=f"Page {i+1}: {uploaded_file.name}", use_column_width=True)
        
        submit_button = st.form_submit_button("🚀 Create Exam", type="primary")
        
        if submit_button:
            if not exam_name.strip():
                st.error("❌ Please enter an exam name")
            elif not topic.strip():
                st.error("❌ Please enter a topic")
            elif not uploaded_files:
                st.error("❌ Please upload at least one exam image")
            else:
                # Create exam
                with st.spinner("Creating exam and saving images..."):
                    # Save uploaded images
                    original_image_paths = []
                    for uploaded_file in uploaded_files:
                        # Validate image
                        is_valid, message = validate_image_file(uploaded_file)
                        if not is_valid:
                            st.error(f"❌ {uploaded_file.name}: {message}")
                            continue
                        
                        # Save image
                        image_path = save_uploaded_image(uploaded_file, "static/images/exams", f"exam_{exam_name.replace(' ', '_')}")
                        original_image_paths.append(image_path)
                    
                    if original_image_paths:
                        # Create exam in database
                        exam_id = db_manager.create_exam(
                            title=exam_name.strip(),
                            topic=topic.strip(),
                            grade_level=grade_level,
                            original_image_paths=original_image_paths
                        )
                        
                        st.session_state.exam_created = True
                        st.session_state.current_exam_id = exam_id
                        
                        st.success(f"✅ Exam created successfully! Exam ID: {exam_id}")
                        st.info("🎯 Next step: Go to 'Digitize Exam' to crop individual questions")
    
    # Show existing exams
    st.divider()
    st.subheader("📚 Existing Exams")
    
    try:
        exams = db_manager.list_exams()
        if exams:
            # Simple list display - click to expand
            for exam in exams[:10]:  # Show last 10 exams
                # Simple one-line display with expand button
                col1, col2 = st.columns([4, 1])
                with col1:
                    exam_display = f"📝 **{exam['name']}** - {exam['topic']} - {exam['grade_level']} ({exam['question_count']} câu)"
                    st.write(exam_display)
                
                with col2:
                    if st.button("📋", key=f"expand_{exam['id']}", help="View details"):
                        # Store selected exam in session state to show details
                        if 'selected_exam_details' not in st.session_state:
                            st.session_state.selected_exam_details = None
                        
                        if st.session_state.selected_exam_details == exam['id']:
                            st.session_state.selected_exam_details = None  # Collapse
                        else:
                            st.session_state.selected_exam_details = exam['id']  # Expand
                        st.rerun()
                
                # Show details if this exam is selected
                if st.session_state.get('selected_exam_details') == exam['id']:
                    with st.container():
                        st.markdown("---")
                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.write(f"**ID:** {exam['id']}")
                        with col2:
                            st.write(f"**Topic:** {exam['topic']}")
                        with col3:
                            st.write(f"**Questions:** {exam['question_count']}")
                        with col4:
                            st.write(f"**Created:** {exam['created_at'].strftime('%Y-%m-%d')}")
                        
                        # Action buttons
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            if st.button(f"🔧 Digitize", key=f"digitize_{exam['id']}"):
                                st.session_state.current_exam_id = exam['id']
                                st.session_state.page = "✂️ Digitize Exam"
                                st.rerun()
                        with col2:
                            if st.button(f"👥 Submissions", key=f"submissions_{exam['id']}"):
                                st.session_state.page = "👥 Student Submissions"
                                st.rerun()
                        with col3:
                            st.caption(f"ID: {exam['id']}")
                        st.markdown("---")
        else:
            st.info("No exams created yet. Create your first exam above!")
            
    except Exception as e:
        st.error(f"Error loading exams: {e}")
    
def show_digitize_exam_page():
    """Page for digitizing exams with cropping"""
    st.header("✂️ Digitize Exam Questions")
    st.markdown("Crop individual questions from the exam paper to create a structured question bank.")
    
    # Initialize session state
    if 'selected_exam_id' not in st.session_state:
        st.session_state.selected_exam_id = None
    if 'current_page_index' not in st.session_state:
        st.session_state.current_page_index = 0
    if 'cropped_questions' not in st.session_state:
        st.session_state.cropped_questions = []
    if 'last_saved_question' not in st.session_state:
        st.session_state.last_saved_question = None
    
    # Show persistent success message if exists
    if st.session_state.last_saved_question:
        st.success(f"🎉 **LAST SAVED:** {st.session_state.last_saved_question}")
        if st.button("✅ Clear notification"):
            st.session_state.last_saved_question = None
            st.rerun()
    
    # Exam selection
    st.subheader("📚 Select Exam to Digitize")
    
    try:
        exams = db_manager.list_exams()
        if not exams:
            st.warning("⚠️ No exams found. Please create an exam first.")
            if st.button("➕ Create New Exam"):
                st.session_state.page = "📝 Create Exam"
                st.rerun()
            return
        
        # Exam selector
        exam_options = [f"{exam['name']} - {exam['topic']} - {exam['grade_level']} (ID: {exam['id']}) - {exam['question_count']} questions" for exam in exams]
        selected_exam_idx = st.selectbox(
            "Choose an exam to digitize:",
            range(len(exams)),
            format_func=lambda x: exam_options[x],
            index=0
        )
        
        selected_exam = exams[selected_exam_idx]
        st.session_state.selected_exam_id = selected_exam['id']
        
        # Get exam details
        exam_details = db_manager.get_exam_by_id(selected_exam['id'])
        if not exam_details:
            st.error("❌ Exam not found!")
            return
            
        st.info(f"🎯 **Selected:** {exam_details.name} | **Grade:** {exam_details.grade_level}")
        
        # Show existing questions for this exam
        existing_questions = db_manager.get_questions_by_exam(selected_exam['id'])
        if existing_questions:
            with st.expander(f"📋 Existing Questions ({len(existing_questions)})"):
                # Group questions by order_index for better organization
                from collections import defaultdict
                grouped_questions = defaultdict(list)
                for q in existing_questions:
                    grouped_questions[q.order_index].append(q)
                
                for order_index in sorted(grouped_questions.keys()):
                    questions_in_group = grouped_questions[order_index]
                    
                    if len(questions_in_group) == 1:
                        # Single question
                        q = questions_in_group[0]
                        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                        with col1:
                            st.write(f"**{format_question_label(q.order_index, q.part_label)}**")
                        with col2:
                            if hasattr(q, 'has_multiple_images') and q.has_multiple_images:
                                try:
                                    image_paths = json.loads(q.question_image_paths)
                                    st.caption(f"📷 {len(image_paths)} images")
                                    if image_paths and os.path.exists(image_paths[0]):
                                        st.image(image_paths[0], width=150)
                                        if len(image_paths) > 1:
                                            st.caption("+ more...")
                                    else:
                                        st.write("❌ Images missing")
                                except:
                                    if os.path.exists(q.question_image_path):
                                        st.image(q.question_image_path, width=150)
                                    else:
                                        st.write("❌ Image missing")
                            else:
                                if os.path.exists(q.question_image_path):
                                    st.image(q.question_image_path, width=150)
                                else:
                                    st.write("❌ Image missing")
                        with col3:
                            st.caption(f"ID: {q.id}")
                        with col4:
                            if st.button("🗑️", key=f"delete_single_{q.id}", help="Delete question"):
                                # Store question to delete in session state for confirmation
                                st.session_state.question_to_delete = {
                                    'id': q.id,
                                    'label': format_question_label(q.order_index, q.part_label),
                                    'type': 'single'
                                }
                                st.rerun()
                    else:
                        # Multi-part question group
                        st.markdown(f"**📄 Question {order_index} ({len(questions_in_group)} parts):**")
                        for q in questions_in_group:
                            col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
                            with col1:
                                st.write(f"  ↳ **{format_question_label(q.order_index, q.part_label)}**")
                            with col2:
                                if hasattr(q, 'has_multiple_images') and q.has_multiple_images:
                                    try:
                                        image_paths = json.loads(q.question_image_paths)
                                        st.caption(f"📷 {len(image_paths)}")
                                        if image_paths and os.path.exists(image_paths[0]):
                                            st.image(image_paths[0], width=120)
                                        else:
                                            st.write("❌ Images missing")
                                    except:
                                        if os.path.exists(q.question_image_path):
                                            st.image(q.question_image_path, width=120)
                                        else:
                                            st.write("❌ Image missing")
                                else:
                                    if os.path.exists(q.question_image_path):
                                        st.image(q.question_image_path, width=120)
                                    else:
                                        st.write("❌ Image missing")
                            with col3:
                                st.caption(f"ID: {q.id}")
                            with col4:
                                if st.button("🗑️", key=f"delete_multi_{q.id}", help="Delete question"):
                                    # Store question to delete in session state for confirmation
                                    st.session_state.question_to_delete = {
                                        'id': q.id,
                                        'label': format_question_label(q.order_index, q.part_label),
                                        'type': 'multi'
                                    }
                                    st.rerun()
                        st.divider()
        
        # Show delete confirmation dialog
        if st.session_state.get('question_to_delete'):
            question_info = st.session_state.question_to_delete
            
            st.warning(f"⚠️ **Confirm Deletion**")
            st.write(f"Are you sure you want to delete **{question_info['label']}**?")
            st.write("This action cannot be undone and will also delete:")
            st.write("- Related student answers")
            st.write("- Related grading results")
            
            col1, col2, col3 = st.columns([1, 1, 2])
            with col1:
                if st.button("❌ Delete", type="primary", key="confirm_delete"):
                    with st.spinner(f"Deleting {question_info['label']}..."):
                        success = db_manager.delete_question(question_info['id'])
                        if success:
                            st.success(f"✅ Successfully deleted {question_info['label']}")
                            st.session_state.question_to_delete = None
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Failed to delete {question_info['label']}")
            
            with col2:
                if st.button("Cancel", key="cancel_delete"):
                    st.session_state.question_to_delete = None
                    st.rerun()
            
            st.divider()
        
        st.divider()
        
        # Load exam images
        original_image_paths = json.loads(exam_details.original_image_paths)
        if not original_image_paths:
            st.warning("⚠️ No exam images found for this exam.")
            return
        
        # Page navigation
        st.subheader(f"📄 Exam Pages ({len(original_image_paths)} total)")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Previous Page") and st.session_state.current_page_index > 0:
                st.session_state.current_page_index -= 1
                st.rerun()
        
        with col2:
            page_options = [f"Page {i+1}" for i in range(len(original_image_paths))]
            current_page = st.selectbox(
                "Select page to work on:",
                range(len(original_image_paths)),
                format_func=lambda x: page_options[x],
                index=st.session_state.current_page_index
            )
            st.session_state.current_page_index = current_page
        
        with col3:
            if st.button("Next Page ➡️") and st.session_state.current_page_index < len(original_image_paths) - 1:
                st.session_state.current_page_index += 1
                st.rerun()
        
        # Display current page for cropping
        current_image_path = original_image_paths[st.session_state.current_page_index]
        
        if os.path.exists(current_image_path):
            st.subheader(f"✂️ Crop Questions from Page {st.session_state.current_page_index + 1}")
            
            # Load image for cropping  
            current_image = Image.open(current_image_path)
            
            # Cropping interface
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("**🎯 Crop a question by dragging to select the area:**")
                cropped_img = st_cropper(
                    current_image,
                    realtime_update=True,
                    box_color="#0066CC",
                    aspect_ratio=None,  # Free-form cropping
                    return_type="image"
                )
            
            with col2:
                st.markdown("**📝 Question Details:**")
                
                # Multi-image question option
                multi_image_mode = st.checkbox(
                    "📷 Multi-image Question", 
                    help="Enable this to add multiple images to the same question",
                    key="multi_image_toggle"
                )
                
                if multi_image_mode:
                    st.info("🔹 Multi-image mode: You can crop multiple parts for the same question")
                    
                    # Initialize multi-image storage
                    if 'current_question_images' not in st.session_state:
                        st.session_state.current_question_images = []
                    
                    # Show current images count
                    if st.session_state.current_question_images:
                        st.success(f"✅ {len(st.session_state.current_question_images)} images added for this question")
                        
                        # Preview current images
                        cols = st.columns(min(len(st.session_state.current_question_images), 3))
                        for i, img in enumerate(st.session_state.current_question_images):
                            with cols[i % 3]:
                                st.image(img, caption=f"Image {i+1}", width=100)
                        
                        if st.button("🗑️ Clear all images", key="clear_multi_images"):
                            st.session_state.current_question_images = []
                            st.rerun()
                
                # Question labeling form
                with st.form("question_form", clear_on_submit=True):
                    question_label = st.text_input(
                        "Question Label",
                        placeholder="e.g., 1a, 2b, 3",
                        help="Enter the question label (same label can have multiple images)"
                    )
                    
                    # Option to replace existing questions
                    replace_if_exists = st.checkbox(
                        "🔄 Replace if question already exists",
                        help="Check this to overwrite existing questions with the same label"
                    )
                    
                    # Preview cropped image
                    if cropped_img:
                        st.markdown("**🖼️ Cropped Preview:**")
                        st.image(cropped_img, width=200)
                        
                        crop_width = cropped_img.width
                        crop_height = cropped_img.height
                        st.caption(f"Size: {crop_width}×{crop_height} px")
                    
                    # Form submit buttons
                    if multi_image_mode:
                        col1, col2 = st.columns(2)
                        with col1:
                            add_image_btn = st.form_submit_button("📷 Add Image", type="secondary")
                        with col2:
                            save_question = st.form_submit_button("💾 Save Question", type="primary")
                    else:
                        save_question = st.form_submit_button("💾 Save Question", type="primary")
                        add_image_btn = False
                
                # Handle add image button
                if add_image_btn:
                    if not cropped_img:
                        st.error("❌ Please crop an image first")
                    else:
                        if 'current_question_images' not in st.session_state:
                            st.session_state.current_question_images = []
                        
                        # Add cropped image to the collection
                        st.session_state.current_question_images.append(cropped_img)
                        st.success(f"✅ Added image {len(st.session_state.current_question_images)} to question")
                        st.rerun()
                
                # Handle form submission outside the form
                if save_question:
                    if not question_label.strip():
                        st.error("❌ Please enter a question label")
                    elif multi_image_mode and not st.session_state.get('current_question_images'):
                        st.error("❌ Please add at least one image in multi-image mode")
                    elif not multi_image_mode and not cropped_img:
                        st.error("❌ Please crop a question area first")
                    else:
                        # Parse question label
                        order_index, part_label = parse_question_label(question_label)
                        
                        # Check if question already exists
                        existing_q = None
                        for q in existing_questions:
                            if q.order_index == order_index and q.part_label == part_label:
                                existing_q = q
                                break
                        
                        if existing_q and not replace_if_exists:
                            st.warning(f"⚠️ Question {format_question_label(order_index, part_label)} already exists!")
                            st.info("💡 Check 'Replace if question already exists' to overwrite it.")
                        else:
                            # Save question (new or replacement)
                            with st.spinner("Saving question..."):
                                if multi_image_mode:
                                    # Multi-image mode: save all collected images
                                    image_paths = save_multiple_cropped_images(
                                        st.session_state.current_question_images,
                                        "static/images/questions",
                                        f"q_{order_index}_{part_label}"
                                    )
                                    
                                    # Create question with multiple images
                                    question_id = db_manager.create_question(
                                        exam_id=selected_exam['id'],
                                        question_image_path=image_paths[0],  # First image for backward compatibility
                                        question_image_paths=image_paths,
                                        has_multiple_images=True,
                                        order_index=order_index,
                                        part_label=part_label
                                    )
                                    
                                    image_info = f"{len(image_paths)} images"
                                    
                                    # Clear the collected images
                                    st.session_state.current_question_images = []
                                    
                                else:
                                    # Single image mode
                                    image_path = save_cropped_image(
                                        cropped_img, 
                                        "static/images/questions",
                                        f"q_{order_index}_{part_label}"
                                    )
                                    
                                    # Create question with single image
                                    question_id = db_manager.create_question(
                                        exam_id=selected_exam['id'],
                                        question_image_path=image_path,
                                        order_index=order_index,
                                        part_label=part_label
                                    )
                                    
                                    image_info = os.path.basename(image_path)
                                
                                action = "Replaced" if existing_q else "Saved"
                                question_label_formatted = format_question_label(order_index, part_label)
                                
                                # Store success message in session state for persistence
                                st.session_state.last_saved_question = f"{action} {question_label_formatted} (ID: {question_id}) - {image_info}"
                                
                                # Success notifications
                                st.success(f"🎉 **SUCCESS!** {action} {question_label_formatted}")
                                st.success(f"📊 **Database ID:** {question_id}")
                                st.success(f"📁 **Images saved:** {image_info}")
                                
                                # Toast notification
                                try:
                                    st.toast(f"🎯 Question {question_label_formatted} saved successfully!", icon="✅")
                                except:
                                    pass
                                
                                # Celebration animation
                                st.balloons()
                                
                                # Auto-clear form and rerun after short delay
                                time.sleep(1.5)
                                st.rerun()
        else:
            st.error(f"❌ Image not found: {current_image_path}")
            
    except Exception as e:
        st.error(f"Error: {e}")
        st.write("Debug info:", str(e))
    
def show_submissions_page():
    """Page for managing student submissions"""
    st.header("👥 Student Submissions")
    st.markdown("Upload student answer sheets and map them to exam questions.")
    
    # Initialize session state
    if 'current_submission_id' not in st.session_state:
        st.session_state.current_submission_id = None
    if 'mapping_mode' not in st.session_state:
        st.session_state.mapping_mode = False
    if 'selected_question_for_mapping' not in st.session_state:
        st.session_state.selected_question_for_mapping = None
    
    # Show success message if exists
    if st.session_state.get('last_submission_created'):
        st.success(f"🎉 **Last Created:** {st.session_state.last_submission_created}")
        if st.button("✅ Clear notification"):
            st.session_state.last_submission_created = None
            st.rerun()
    
    # Submission creation section
    st.subheader("📝 Create New Submission")
    
    # Get available exams
    try:
        exams = db_manager.list_exams()
        if not exams:
            st.warning("⚠️ No exams found. Please create an exam first.")
            if st.button("➕ Create New Exam"):
                st.session_state.page = "📝 Create Exam"
                st.rerun()
            return
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**📚 Select Exam**")
            exam_options = [f"{exam['name']} - {exam['topic']} - {exam['grade_level']} (ID: {exam['id']}) - {exam['question_count']} questions" for exam in exams]
            selected_exam_idx = st.selectbox(
                "Choose exam to grade:",
                range(len(exams)),
                format_func=lambda x: exam_options[x],
                help="Select which exam this student submission belongs to"
            )
            
            selected_exam = exams[selected_exam_idx]
            
            # Show exam info
            st.info(f"📋 **Selected Exam:** {selected_exam['name']}")
            st.info(f"📊 **Questions:** {selected_exam['question_count']}")
        
        with col2:
            st.markdown("**👤 Student Information**")
            student_name = st.text_input(
                "Student Name",
                placeholder="Nguyễn Văn A",
                help="Enter the student's full name"
            )
            
            st.markdown("**📷 Upload Answer Sheets**")
            uploaded_files = st.file_uploader(
                "Select answer sheet images",
                type=["png", "jpg", "jpeg"],
                accept_multiple_files=True,
                help="Upload all pages of the student's answer sheet"
            )
            
            # Preview uploaded images
            if uploaded_files:
                st.success(f"✅ {len(uploaded_files)} image(s) selected")
                if st.checkbox("Preview uploaded images"):
                    cols = st.columns(min(len(uploaded_files), 3))
                    for i, uploaded_file in enumerate(uploaded_files[:3]):
                        with cols[i]:
                            image = Image.open(uploaded_file)
                            st.image(image, caption=f"Page {i+1}", width=200)
                    if len(uploaded_files) > 3:
                        st.caption(f"... and {len(uploaded_files) - 3} more images")
        
        # Create submission button
        if uploaded_files and student_name.strip():
            if st.button("🚀 Create Submission", type="primary", use_container_width=True):
                with st.spinner("Creating submission and saving images..."):
                    # Save uploaded images
                    original_image_paths = []
                    for uploaded_file in uploaded_files:
                        # Validate image
                        is_valid, message = validate_image_file(uploaded_file)
                        if not is_valid:
                            st.error(f"❌ {uploaded_file.name}: {message}")
                            continue
                        
                        # Save image
                        image_path = save_uploaded_image(
                            uploaded_file, 
                            "static/images/submissions", 
                            f"student_{student_name.replace(' ', '_')}"
                        )
                        original_image_paths.append(image_path)
                    
                    if original_image_paths:
                        # Create submission in database
                        submission_id = db_manager.create_submission(
                            exam_id=selected_exam['id'],
                            student_name=student_name.strip(),
                            original_image_paths=original_image_paths
                        )
                        
                        st.session_state.current_submission_id = submission_id
                        st.session_state.last_submission_created = f"Submission for {student_name} (ID: {submission_id})"
                        st.session_state.mapping_mode = True
                        
                        st.success(f"✅ Submission created successfully! ID: {submission_id}")
                        st.info("🎯 Next: Map student answers to questions below")
                        st.rerun()
        elif uploaded_files:
            st.warning("❌ Please enter student name")
        elif student_name.strip():
            st.warning("❌ Please upload answer sheet images")
        
    except Exception as e:
        st.error(f"Error loading exams: {e}")
        return
    
    st.divider()
    
    # Answer mapping section
    st.subheader("✂️ Answer Mapping")
    
    # Show existing submissions
    if st.session_state.current_submission_id:
        show_answer_mapping_interface()
    else:
        # Show existing submissions to continue mapping
        try:
            existing_submissions = []
            for exam in exams:
                subs = db_manager.list_submissions_by_exam(exam['id'])
                for sub in subs:
                    existing_submissions.append({
                        **sub,
                        'exam_name': exam['name']
                    })
            
            if existing_submissions:
                st.markdown("**📋 Continue with existing submission:**")
                
                submission_options = [
                    f"{sub['student_name']} - {sub['exam_name']} (ID: {sub['id']})"
                    for sub in existing_submissions[-10:]  # Show last 10
                ]
                
                selected_sub_idx = st.selectbox(
                    "Select submission to continue mapping:",
                    range(len(submission_options)),
                    format_func=lambda x: submission_options[x]
                )
                
                if st.button("📝 Continue Mapping", type="secondary"):
                    selected_submission = existing_submissions[-10:][selected_sub_idx]
                    st.session_state.current_submission_id = selected_submission['id']
                    st.session_state.mapping_mode = True
                    st.rerun()
            else:
                st.info("💡 Create a submission above to start answer mapping")
                
        except Exception as e:
            st.error(f"Error loading submissions: {e}")

def show_answer_mapping_interface():
    """Show the answer mapping interface for current submission"""
    submission_id = st.session_state.current_submission_id
    
    try:
        # Get submission details
        submission = db_manager.get_submission_by_id(submission_id)
        if not submission:
            st.error("❌ Submission not found")
            return
        
        st.info(f"🎯 **Current Submission:** {submission.student_name} (ID: {submission_id})")
        
        # Get exam questions
        questions = db_manager.get_questions_by_exam(submission.exam_id)
        if not questions:
            st.warning("⚠️ No questions found for this exam")
            return
        
        # Get submission images
        original_images = json.loads(submission.original_image_paths)
        if not original_images:
            st.warning("⚠️ No submission images found")
            return
        
        # Get existing submission items (already mapped answers)
        existing_items = db_manager.get_submission_items(submission_id)
        mapped_questions = {item.question_id for item in existing_items}
        
        st.markdown(f"**📊 Progress:** {len(mapped_questions)}/{len(questions)} questions mapped")
        
        # Two column layout for mapping
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.markdown("**📝 Questions to Map**")
            
            # Group questions by order_index
            from collections import defaultdict
            grouped_questions = defaultdict(list)
            for q in questions:
                grouped_questions[q.order_index].append(q)
            
            # Show questions with mapping status
            for order_index in sorted(grouped_questions.keys()):
                questions_in_group = grouped_questions[order_index]
                
                for question in questions_in_group:
                    is_mapped = question.id in mapped_questions
                    status_icon = "✅" if is_mapped else "⏳"
                    
                    question_label = format_question_label(question.order_index, question.part_label)
                    
                    if st.button(
                        f"{status_icon} {question_label}",
                        key=f"select_q_{question.id}",
                        use_container_width=True,
                        type="secondary" if is_mapped else "primary",
                        help="Click to remap" if is_mapped else "Click to map answer"
                    ):
                        if is_mapped:
                            st.info(f"⚠️ **{question_label}** is already mapped. Proceeding will update the existing mapping.")
                        st.session_state.selected_question_for_mapping = question.id
                        st.rerun()
                    
                    # Show question preview
                    if hasattr(question, 'has_multiple_images') and question.has_multiple_images:
                        # Multi-image question
                        try:
                            image_paths = json.loads(question.question_image_paths)
                            st.caption(f"📷 {len(image_paths)} images")
                            # Show first image as preview
                            if image_paths and os.path.exists(image_paths[0]):
                                st.image(image_paths[0], width=150)
                                if len(image_paths) > 1:
                                    st.caption("+ more images...")
                            else:
                                st.write("❌ Question images missing")
                        except:
                            # Fallback to single image
                            if os.path.exists(question.question_image_path):
                                st.image(question.question_image_path, width=150)
                            else:
                                st.write("❌ Question image missing")
                    else:
                        # Single image question
                        if os.path.exists(question.question_image_path):
                            st.image(question.question_image_path, width=150)
                        else:
                            st.write("❌ Question image missing")
                    
                    st.markdown("---")
        
        with col2:
            st.markdown("**🎯 Answer Mapping**")
            
            if st.session_state.selected_question_for_mapping:
                show_answer_cropping_interface(original_images)
            else:
                st.info("👈 Select a question from the left to start mapping answers")
                
                # Show submission images for reference
                st.markdown("**📄 Student's Answer Sheet Pages:**")
                for i, image_path in enumerate(original_images):
                    if os.path.exists(image_path):
                        st.image(image_path, caption=f"Page {i+1}", width=400)
                    else:
                        st.write(f"❌ Image {i+1} not found")
        
        # Action buttons
        st.divider()
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("🔙 Back to Submissions"):
                st.session_state.current_submission_id = None
                st.session_state.mapping_mode = False
                st.session_state.selected_question_for_mapping = None
                st.rerun()
        
        with col2:
            if len(mapped_questions) > 0:
                if st.button("🎯 Start Grading", type="primary"):
                    st.session_state.page = "🎯 Grade Submissions"
                    st.rerun()
        
        with col3:
            completion_rate = len(mapped_questions) / len(questions) * 100
            st.metric("Completion", f"{completion_rate:.0f}%")
            
    except Exception as e:
        st.error(f"Error in answer mapping: {e}")

def show_answer_cropping_interface(original_images):
    """Show interface for cropping student answers"""
    question_id = st.session_state.selected_question_for_mapping
    
    # Initialize answer cropping page index in session state
    if f'answer_crop_page_{question_id}' not in st.session_state:
        st.session_state[f'answer_crop_page_{question_id}'] = 0
    
    # Get question details
    question = db_manager.get_question_by_id(question_id)
    if not question:
        st.error("❌ Question not found")
        return
    
    question_label = format_question_label(question.order_index, question.part_label)
    st.markdown(f"**🎯 Mapping Answer for: {question_label}**")
    
    # Show question image(s) for reference
    if hasattr(question, 'has_multiple_images') and question.has_multiple_images:
        # Multi-image question
        try:
            image_paths = json.loads(question.question_image_paths)
            with st.expander(f"📝 Question Reference ({len(image_paths)} images)", expanded=False):
                st.markdown(f"**🎯 Question {question_label} - Multiple Images:**")
                for i, img_path in enumerate(image_paths, 1):
                    if os.path.exists(img_path):
                        st.image(img_path, caption=f"Question Part {i}", width=300)
                        st.markdown("---")
                    else:
                        st.write(f"❌ Question image {i} missing")
        except:
            # Fallback to single image
            if os.path.exists(question.question_image_path):
                with st.expander("📝 Question Reference", expanded=False):
                    st.image(question.question_image_path, caption=f"Question {question_label}", width=400)
    else:
        # Single image question
        if os.path.exists(question.question_image_path):
            with st.expander("📝 Question Reference", expanded=False):
                st.image(question.question_image_path, caption=f"Question {question_label}", width=400)
    
    # Page selection for cropping with session state support
    if len(original_images) > 1:
        st.markdown("**📄 Select page to crop answer from:**")
        
        # Page navigation buttons similar to question cropping
        col1, col2, col3 = st.columns([1, 2, 1])
        with col1:
            if st.button("⬅️ Previous Page", key=f"prev_page_{question_id}") and st.session_state[f'answer_crop_page_{question_id}'] > 0:
                st.session_state[f'answer_crop_page_{question_id}'] -= 1
                st.rerun()
        
        with col2:
            page_options = [f"Page {i+1}" for i in range(len(original_images))]
            current_page = st.selectbox(
                "Choose page:",
                range(len(original_images)),
                format_func=lambda x: page_options[x],
                index=st.session_state[f'answer_crop_page_{question_id}'],
                key=f"page_select_{question_id}"
            )
            # Update session state when selectbox changes
            st.session_state[f'answer_crop_page_{question_id}'] = current_page
        
        with col3:
            if st.button("Next Page ➡️", key=f"next_page_{question_id}") and st.session_state[f'answer_crop_page_{question_id}'] < len(original_images) - 1:
                st.session_state[f'answer_crop_page_{question_id}'] += 1
                st.rerun()
        
        selected_page_idx = st.session_state[f'answer_crop_page_{question_id}']
    else:
        selected_page_idx = 0
    
    # Show selected page for cropping
    selected_image_path = original_images[selected_page_idx]
    
    if os.path.exists(selected_image_path):
        st.markdown(f"**✂️ Crop answer from Page {selected_page_idx + 1}:**")
        
        # Load image for cropping
        current_image = Image.open(selected_image_path)
        
        # Multi-image answer option - place above cropping area
        st.markdown("**📝 Answer Options:**")
        col1, col2 = st.columns([1, 3])
        
        with col1:
            multi_image_mode = st.checkbox(
                "📷 Multi-image Answer", 
                help="Enable this to add multiple answer parts from different pages",
                key=f"multi_image_answer_toggle_{question_id}"
            )
        
        with col2:
            if multi_image_mode:
                # Initialize multi-image storage
                if f'current_answer_images_{question_id}' not in st.session_state:
                    st.session_state[f'current_answer_images_{question_id}'] = []
                
                # Show current images count inline
                if st.session_state[f'current_answer_images_{question_id}']:
                    st.success(f"✅ {len(st.session_state[f'current_answer_images_{question_id}'])} parts added", icon="📷")
                else:
                    st.info("🔹 Multi-image mode active - crop multiple answer parts")
        
        st.markdown("---")
        
        # Full-width cropping interface
        st.markdown("**✂️ Cropping Area:**")
        cropped_answer = st_cropper(
            current_image,
            realtime_update=True,
            box_color="#FF6B6B",  # Different color for answers
            aspect_ratio=None,
            return_type="image",
            key=f"answer_crop_{question_id}_page_{selected_page_idx}"
        )
        
        # Multi-image preview section (only when there are images to show)
        if multi_image_mode and st.session_state[f'current_answer_images_{question_id}']:
            st.markdown("**🖼️ Collected Answer Parts:**")
            cols = st.columns(min(len(st.session_state[f'current_answer_images_{question_id}']), 4))
            for i, img in enumerate(st.session_state[f'current_answer_images_{question_id}']):
                with cols[i % 4]:
                    st.image(img, caption=f"Part {i+1}", width=120)
            
            if st.button("🗑️ Clear all parts", key=f"clear_multi_answer_{question_id}"):
                st.session_state[f'current_answer_images_{question_id}'] = []
                st.rerun()
        
        if cropped_answer:
            st.markdown("**🖼️ Cropped Answer Preview:**")
            col1, col2 = st.columns([1, 2])
            with col1:
                st.image(cropped_answer, caption=f"Answer for {question_label}", width=250)
            
            with col2:
                st.markdown("**💾 Save Options:**")
                # Button layout
                if multi_image_mode:
                    if st.button("📷 Add Answer Part", type="secondary", key=f"add_answer_part_{question_id}", use_container_width=True):
                        if cropped_answer:
                            st.session_state[f'current_answer_images_{question_id}'].append(cropped_answer)
                            st.success(f"✅ Added part {len(st.session_state[f'current_answer_images_{question_id}'])}")
                            st.rerun()
                        else:
                            st.error("❌ Please crop an answer first")
                    
                    st.markdown("---")
                    save_multi_answer = st.button("💾 Save Multi-Answer", type="primary", key=f"save_multi_answer_{question_id}", use_container_width=True)
                else:
                    save_multi_answer = False
                    save_single_answer = st.button("💾 Save Answer Mapping", type="primary", key=f"save_answer_{question_id}", use_container_width=True)
            
            # Handle save multi-answer
            if multi_image_mode and save_multi_answer:
                if st.session_state[f'current_answer_images_{question_id}']:
                    with st.spinner("Saving multi-image answer mapping..."):
                        try:
                            # Save all answer images
                            answer_image_paths = save_multiple_cropped_images(
                                st.session_state[f'current_answer_images_{question_id}'],
                                "static/images/answers",
                                f"answer_{question.order_index}_{question.part_label}"
                            )
                            
                            # Create submission item with multiple images
                            item_id = db_manager.create_submission_item(
                                submission_id=st.session_state.current_submission_id,
                                question_id=question_id,
                                answer_image_path=answer_image_paths[0],  # First image for backward compatibility
                                answer_image_paths=answer_image_paths,
                                has_multiple_images=True
                            )
                            
                            # Check if this was an update or new mapping
                            existing_items = db_manager.get_submission_items(st.session_state.current_submission_id)
                            is_update = any(item.question_id == question_id for item in existing_items if item.id != item_id)
                            
                            if is_update:
                                st.success(f"🔄 Multi-image answer **updated** for {question_label}!")
                            else:
                                st.success(f"✅ Multi-image answer **saved** for {question_label}!")
                            st.balloons()
                            
                            # Clear all data and refresh
                            st.session_state.selected_question_for_mapping = None
                            st.session_state[f'current_answer_images_{question_id}'] = []
                            time.sleep(1)
                            st.rerun()
                            
                        except Exception as e:
                            st.error(f"❌ Error saving multi-image answer: {e}")
                else:
                    st.error("❌ Please add at least one answer image")
            
            # Handle save single answer
            elif not multi_image_mode and 'save_single_answer' in locals() and save_single_answer:
                with st.spinner("Saving answer mapping..."):
                    try:
                        # Save cropped answer image
                        answer_image_path = save_cropped_image(
                            cropped_answer,
                            "static/images/answers",
                            f"answer_{question.order_index}_{question.part_label}"
                        )
                        
                        # Create submission item
                        item_id = db_manager.create_submission_item(
                            submission_id=st.session_state.current_submission_id,
                            question_id=question_id,
                            answer_image_path=answer_image_path
                        )
                        
                        # Check if this was an update or new mapping
                        existing_items = db_manager.get_submission_items(st.session_state.current_submission_id)
                        is_update = any(item.question_id == question_id for item in existing_items if item.id != item_id)
                        
                        if is_update:
                            st.success(f"🔄 Answer **updated** for {question_label}!")
                        else:
                            st.success(f"✅ Answer **saved** for {question_label}!")
                        st.balloons()
                        
                        # Clear selection and refresh
                        st.session_state.selected_question_for_mapping = None
                        time.sleep(1)
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error saving answer: {e}")
        else:
            st.info("👆 Use the cropping tool above to select the answer area")
    else:
        st.error(f"❌ Image not found: {selected_image_path}")
    
def show_grading_page():
    """Page for grading submissions using Vision AI"""
    st.header("🎯 Grade Student Submissions")
    st.markdown("Automatically grade student answers using GPT-5 Mini Vision AI.")
    
    # Initialize session state
    if 'grading_results' not in st.session_state:
        st.session_state.grading_results = {}
    if 'selected_submission_for_grading' not in st.session_state:
        st.session_state.selected_submission_for_grading = None
    if 'grading_in_progress' not in st.session_state:
        st.session_state.grading_in_progress = False
    
    # Get all submissions with mapped answers
    all_submissions = db_manager.get_all_submissions()
    
    if not all_submissions:
        st.warning("⚠️ No student submissions found. Please create submissions first.")
        if st.button("➕ Go to Submissions Page"):
            st.session_state.page = "👥 Submissions"
            st.rerun()
        return
    
    # Filter submissions that have mapped answers
    submissions_with_answers = []
    for submission in all_submissions:
        submission_items = db_manager.get_submission_items(submission.id)
        if submission_items:
            submissions_with_answers.append((submission, submission_items))
    
    if not submissions_with_answers:
        st.warning("⚠️ No submissions with mapped answers found. Please map answers first.")
        if st.button("🎯 Go to Answer Mapping"):
            st.session_state.page = "👥 Submissions"
            st.rerun()
        return
    
    # Submission selection
    st.markdown("### 📋 Select Submission to Grade")
    
    submission_options = []
    for submission, items in submissions_with_answers:
        exam = db_manager.get_exam_by_id(submission.exam_id)
        exam_name = exam.title if exam else "Unknown Exam"
        item_count = len(items)
        submission_options.append(f"{submission.student_name} - {exam_name} ({item_count} questions)")
    
    if submission_options:
        selected_idx = st.selectbox(
            "Choose submission to grade:",
            range(len(submission_options)),
            format_func=lambda x: submission_options[x],
            key="submission_selector"
        )
        
        selected_submission, selected_items = submissions_with_answers[selected_idx]
        st.session_state.selected_submission_for_grading = selected_submission.id
        
        # Show submission details
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Student", selected_submission.student_name)
        with col2:
            exam = db_manager.get_exam_by_id(selected_submission.exam_id)
            st.metric("Exam", exam.title if exam else "Unknown")
        with col3:
            st.metric("Questions", len(selected_items))
        
        st.divider()
        
        # Show grading interface
        show_grading_interface(selected_submission, selected_items)

def show_grading_interface(submission, submission_items):
    """Interface for grading individual questions"""
    st.markdown("### 🔍 Question by Question Grading")
    
    # Get existing gradings
    existing_gradings = {g.submission_item_id: g for g in db_manager.get_gradings_by_submission(submission.id)}
    
    # Progress tracking
    graded_count = len(existing_gradings)
    total_count = len(submission_items)
    progress = graded_count / total_count if total_count > 0 else 0
    
    col1, col2 = st.columns([3, 1])
    with col1:
        st.progress(progress, text=f"Progress: {graded_count}/{total_count} questions graded")
    with col2:
        if graded_count == total_count:
            st.success("✅ Complete!")
        else:
            st.info(f"⏳ {total_count - graded_count} left")
    
    # Batch grading option
    st.markdown("### ⚡ Batch Processing")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🚀 Grade All Remaining", type="primary", disabled=st.session_state.grading_in_progress):
            if graded_count < total_count:
                grade_batch_submission(submission, submission_items, existing_gradings)
            else:
                st.info("All questions already graded!")
    
    with col2:
        if existing_gradings and st.button("🔄 Re-grade All", disabled=st.session_state.grading_in_progress):
            # Clear existing gradings and re-grade
            for grading in existing_gradings.values():
                db_manager.delete_grading(grading.id)
            grade_batch_submission(submission, submission_items, {})
    
    with col3:
        if existing_gradings:
            correct_count = sum(1 for g in existing_gradings.values() if g.is_correct)
            accuracy = correct_count / len(existing_gradings) * 100
            st.metric("Accuracy", f"{accuracy:.1f}%")
    
    st.divider()
    
    # Show delete confirmation dialog
    if st.session_state.get('question_to_delete_from_grading'):
        question_info = st.session_state.question_to_delete_from_grading
        
        st.warning(f"⚠️ **Confirm Deletion of {question_info['label']}**")
        st.write(f"Are you sure you want to delete **{question_info['label']}**?")
        st.write("This action will permanently remove:")
        st.write("- ❌ The question from the exam")
        st.write("- ❌ All student answers for this question")
        st.write("- ❌ All grading results for this question")
        st.write("- ❌ All associated image files")
        
        col1, col2, col3 = st.columns([1, 1, 2])
        with col1:
            if st.button("❌ Delete", type="primary", key="confirm_delete_grading"):
                with st.spinner(f"Deleting {question_info['label']}..."):
                    success = db_manager.delete_question(question_info['id'])
                    if success:
                        st.success(f"✅ Successfully deleted {question_info['label']}")
                        st.session_state.question_to_delete_from_grading = None
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"❌ Failed to delete {question_info['label']}")
        
        with col2:
            if st.button("Cancel", key="cancel_delete_grading"):
                st.session_state.question_to_delete_from_grading = None
                st.rerun()
        
        st.divider()
    
    # Individual question grading
    st.markdown("### 📝 Individual Questions")
    
    for item in submission_items:
        question = db_manager.get_question_by_id(item.question_id)
        if not question:
            continue
        
        question_label = format_question_label(question.order_index, question.part_label)
        existing_grading = existing_gradings.get(item.id)
        
        # Create expandable section for each question with delete option
        col1, col2 = st.columns([4, 1])
        with col1:
            expanded = not existing_grading
            expander = st.expander(f"Question {question_label} {'✅' if existing_grading else '⏳'}", expanded=expanded)
        with col2:
            if st.button("🗑️", key=f"delete_grading_q_{question.id}", help=f"Delete {question_label}", type="secondary"):
                st.session_state.question_to_delete_from_grading = {
                    'id': question.id,
                    'label': question_label,
                    'submission_id': submission.id
                }
                st.rerun()
        
        with expander:
            show_single_question_grading(item, question, existing_grading)

def show_single_question_grading(submission_item, question, existing_grading=None):
    """Interface for grading a single question"""
    question_label = format_question_label(question.order_index, question.part_label)
    
    # Show images side by side
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**📝 Question:**")
        if hasattr(question, 'has_multiple_images') and question.has_multiple_images:
            # Multi-image question
            try:
                image_paths = json.loads(question.question_image_paths)
                st.caption(f"📷 Multi-image question ({len(image_paths)} parts)")
                for i, img_path in enumerate(image_paths, 1):
                    if os.path.exists(img_path):
                        st.image(img_path, caption=f"Question Part {i}", use_column_width=True)
                        if i < len(image_paths):  # Add separator except for last image
                            st.markdown("---")
                    else:
                        st.error(f"❌ Question image {i} not found")
            except:
                # Fallback to single image
                if os.path.exists(question.question_image_path):
                    st.image(question.question_image_path, caption=f"Question {question_label}", use_column_width=True)
                else:
                    st.error("❌ Question image not found")
        else:
            # Single image question
            if os.path.exists(question.question_image_path):
                st.image(question.question_image_path, caption=f"Question {question_label}", use_column_width=True)
            else:
                st.error("❌ Question image not found")
    
    with col2:
        st.markdown("**✍️ Student Answer:**")
        # Check for multiple answer images
        if hasattr(submission_item, 'has_multiple_images') and submission_item.has_multiple_images:
            try:
                answer_paths = json.loads(submission_item.answer_image_paths)
                st.markdown(f"**Multiple Answer Parts ({len(answer_paths)} images):**")
                for i, img_path in enumerate(answer_paths, 1):
                    if os.path.exists(img_path):
                        st.image(img_path, caption=f"Answer Part {i}", width=250)
                        if i < len(answer_paths):  # Don't show divider after last image
                            st.markdown("---")
                    else:
                        st.write(f"❌ Answer image {i} missing")
            except:
                # Fallback to single image
                if os.path.exists(submission_item.answer_image_path):
                    st.image(submission_item.answer_image_path, caption=f"Student's answer", use_column_width=True)
                else:
                    st.error("❌ Answer image not found")
        else:
            # Single answer image
            if os.path.exists(submission_item.answer_image_path):
                st.image(submission_item.answer_image_path, caption=f"Student's answer", use_column_width=True)
            else:
                st.error("❌ Answer image not found")
    
    # Show existing grading if available
    if existing_grading:
        st.markdown("**🎯 AI Grading Result:**")
        
        # Result display
        col1, col2, col3 = st.columns(3)
        with col1:
            status_color = "green" if existing_grading.is_correct else "red"
            result_text = "CORRECT ✅" if existing_grading.is_correct else "INCORRECT ❌"
            st.markdown(f"**Result:** :{status_color}[{result_text}]")
        
        with col2:
            if existing_grading.confidence:
                st.metric("Confidence", f"{existing_grading.confidence:.1%}")
        
        with col3:
            if existing_grading.partial_credit:
                st.info("🔄 Partial Credit")
        
        # Error description and phrases
        if existing_grading.error_description and existing_grading.error_description != "No errors found":
            st.markdown("**🔍 Error Analysis:**")
            st.warning(existing_grading.error_description)
            
            # Display error phrases if available
            if hasattr(existing_grading, 'error_phrases') and existing_grading.error_phrases:
                try:
                    error_phrases = json.loads(existing_grading.error_phrases)
                    if error_phrases:
                        st.markdown("**⚠️ Specific Error Points:**")
                        for i, phrase in enumerate(error_phrases, 1):
                            st.markdown(f"• **{i}.** {phrase}")
                except:
                    pass  # Skip if error_phrases is not valid JSON
        
        # Teacher override options
        st.markdown("**👨‍🏫 Teacher Override:**")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button(f"✅ Mark Correct", key=f"correct_{submission_item.id}"):
                update_grading_result(existing_grading.id, True, "Teacher override: Marked as correct")
        
        with col2:
            if st.button(f"❌ Mark Incorrect", key=f"incorrect_{submission_item.id}"):
                update_grading_result(existing_grading.id, False, "Teacher override: Marked as incorrect")
        
        with col3:
            if st.button(f"🔄 Re-grade", key=f"regrade_{submission_item.id}"):
                grade_single_question(submission_item, question)
    
    else:
        # Grade this question
        st.markdown("**⏳ Not graded yet**")
        if st.button(f"🚀 Grade Question {question_label}", key=f"grade_{submission_item.id}", type="primary"):
            grade_single_question(submission_item, question)

def grade_single_question(submission_item, question):
    """Grade a single question using Vision AI"""
    try:
        # Validate image paths
        if not os.path.exists(question.question_image_path):
            st.error("❌ Question image not found")
            return
        
        if not os.path.exists(submission_item.answer_image_path):
            st.error("❌ Answer image not found")
            return
        
        # Show loading spinner
        with st.spinner(f"🤖 Grading question {format_question_label(question.order_index, question.part_label)}..."):
            # Get grading service
            grading_service = get_grading_service()
            
            # Prepare question images
            question_image_paths = None
            if hasattr(question, 'has_multiple_images') and question.has_multiple_images:
                try:
                    question_image_paths = json.loads(question.question_image_paths)
                except:
                    question_image_paths = None
            
            # Prepare answer image paths for grading
            answer_image_paths = []
            if hasattr(submission_item, 'has_multiple_images') and submission_item.has_multiple_images:
                try:
                    answer_image_paths = json.loads(submission_item.answer_image_paths)
                except:
                    answer_image_paths = []
            
            # Grade the image pair
            result_dict = grading_service.grade_image_pair(
                question.question_image_path,
                submission_item.answer_image_path,
                question_image_paths=question_image_paths,
                answer_image_paths=answer_image_paths if answer_image_paths else None
            )
            
            # Create grading record
            grading_id = db_manager.create_grading(
                submission_item_id=submission_item.id,
                question_id=question.id,
                is_correct=result_dict['is_correct'],
                confidence=result_dict.get('confidence'),
                error_description=result_dict['error_description'],
                error_phrases=result_dict.get('error_phrases', []),
                partial_credit=result_dict.get('partial_credit', False)
            )
            
            if grading_id:
                st.success(f"✅ Question graded successfully!")
                st.balloons()
                time.sleep(1)
                st.rerun()
            else:
                st.error("❌ Failed to save grading result")
    
    except Exception as e:
        st.error(f"❌ Grading failed: {str(e)}")
        st.write("Please check your OpenAI API key and try again.")

def grade_batch_submission(submission, submission_items, existing_gradings):
    """Grade all remaining questions in a submission"""
    try:
        st.session_state.grading_in_progress = True
        
        # Filter items that need grading
        items_to_grade = []
        for item in submission_items:
            if item.id not in existing_gradings:
                question = db_manager.get_question_by_id(item.question_id)
                if question and os.path.exists(question.question_image_path) and os.path.exists(item.answer_image_path):
                    # Prepare question image paths for multi-image questions
                    question_image_paths = []
                    if hasattr(question, 'has_multiple_images') and question.has_multiple_images:
                        try:
                            question_image_paths = json.loads(question.question_image_paths)
                        except:
                            question_image_paths = []
                    
                    # Prepare answer image paths for multi-image answers
                    answer_image_paths = []
                    if hasattr(item, 'has_multiple_images') and item.has_multiple_images:
                        try:
                            answer_image_paths = json.loads(item.answer_image_paths)
                        except:
                            answer_image_paths = []
                    
                    items_to_grade.append({
                        'question_image_path': question.question_image_path,
                        'answer_image_path': item.answer_image_path,
                        'question_id': question.id,
                        'submission_item_id': item.id,
                        'question_image_paths': question_image_paths if question_image_paths else None,
                        'answer_image_paths': answer_image_paths if answer_image_paths else None
                    })
        
        if not items_to_grade:
            st.warning("⚠️ No questions to grade")
            st.session_state.grading_in_progress = False
            return
        
        # Show batch progress
        progress_bar = st.progress(0, text="Starting batch grading...")
        status_text = st.empty()
        
        # Get grading service
        grading_service = get_grading_service()
        
        # Grade all items
        status_text.text(f"🤖 Grading {len(items_to_grade)} questions...")
        results = grading_service.grade_submission_items(items_to_grade)
        
        # Save results to database
        successful_grades = 0
        for result in results:
            try:
                grading_id = db_manager.create_grading(
                    submission_item_id=result.submission_item_id,
                    question_id=result.question_id,
                    is_correct=result.is_correct,
                    confidence=result.confidence,
                    error_description=result.error_description,
                    error_phrases=result.error_phrases,
                    partial_credit=result.partial_credit
                )
                
                if grading_id:
                    successful_grades += 1
                    
            except Exception as e:
                st.error(f"Failed to save grading for question {result.question_id}: {e}")
        
        # Update progress
        progress_bar.progress(1.0, text="Batch grading completed!")
        
        # Show results
        st.success(f"🎉 Batch grading completed! {successful_grades}/{len(items_to_grade)} questions graded successfully.")
        
        if successful_grades > 0:
            correct_count = sum(1 for r in results if r.is_correct)
            accuracy = correct_count / successful_grades * 100
            st.info(f"📊 Overall accuracy: {accuracy:.1f}% ({correct_count}/{successful_grades} correct)")
            
            st.balloons()
            time.sleep(2)
        
        st.session_state.grading_in_progress = False
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Batch grading failed: {str(e)}")
        st.session_state.grading_in_progress = False

def update_grading_result(grading_id, is_correct, teacher_notes_override):
    """Update an existing grading result with teacher override"""
    try:
        success = db_manager.update_grading(
            grading_id=grading_id,
            is_correct=is_correct,
            teacher_notes=teacher_notes_override
        )
        
        if success:
            st.success(f"✅ Grading updated successfully!")
            time.sleep(1)
            st.rerun()
        else:
            st.error("❌ Failed to update grading")
            
    except Exception as e:
        st.error(f"❌ Update failed: {str(e)}")
    
def show_results_page():
    """Page for viewing results and reports"""
    st.header("📊 Results & Reports")
    st.info("This page will be implemented in Week 5 - Results Display")

if __name__ == "__main__":
    main()