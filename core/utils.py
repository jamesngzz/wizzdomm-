import os
import uuid
from datetime import datetime
from PIL import Image
from typing import List, Tuple
import streamlit as st

from .config import QUESTIONS_DIR, ANSWERS_DIR, SUPPORTED_IMAGE_FORMATS, MAX_IMAGE_SIZE_MB

def save_uploaded_image(uploaded_file, save_dir: str, prefix: str = "") -> str:
    """Save uploaded file to specified directory and return the file path"""
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{prefix}_{timestamp}_{unique_id}_{uploaded_file.name}" if prefix else f"{timestamp}_{unique_id}_{uploaded_file.name}"
    
    # Ensure directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Save file
    file_path = os.path.join(save_dir, filename)
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    return file_path

def save_cropped_image(image: Image.Image, save_dir: str, prefix: str = "") -> str:
    """Save cropped PIL Image to specified directory and return the file path"""
    # Generate unique filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    filename = f"{prefix}_{timestamp}_{unique_id}.png" if prefix else f"{timestamp}_{unique_id}.png"
    
    # Ensure directory exists
    os.makedirs(save_dir, exist_ok=True)
    
    # Save image
    file_path = os.path.join(save_dir, filename)
    image.save(file_path, "PNG")
    
    return file_path

def validate_image_file(uploaded_file) -> Tuple[bool, str]:
    """Validate uploaded image file"""
    if uploaded_file is None:
        return False, "No file uploaded"
    
    # Check file extension
    file_extension = uploaded_file.name.split(".")[-1].lower()
    if file_extension not in SUPPORTED_IMAGE_FORMATS:
        return False, f"Unsupported format. Supported: {', '.join(SUPPORTED_IMAGE_FORMATS)}"
    
    # Enforce max image size from config
    if uploaded_file.size > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        return False, f"File too large. Maximum size: {MAX_IMAGE_SIZE_MB}MB"
    
    return True, "Valid"

def display_image_with_info(image_path: str, caption: str = ""):
    """Display image with file information"""
    if os.path.exists(image_path):
        st.image(image_path, caption=caption, use_container_width=True)
        
        # Show file info
        file_size = os.path.getsize(image_path)
        st.caption(f"📁 {os.path.basename(image_path)} • {file_size:,} bytes")
    else:
        st.error(f"Image not found: {image_path}")

def format_question_label(order_index: int, part_label: str = "") -> str:
    """Format question label for display"""
    if part_label.strip():
        return f"Câu {order_index}{part_label}"
    return f"Câu {order_index}"

def parse_question_label(label: str) -> Tuple[int, str]:
    """Parse question label into order_index and part_label"""
    # Handle formats like "1", "1a", "1.a", "2b", "1a-part1", "1a-p2", etc.
    label = label.strip().lower()
    
    # Remove "câu" prefix if present
    if label.startswith("câu"):
        label = label[3:].strip()
    
    # Extract number and part
    order_index = 1
    part_label = ""
    
    # Find where numbers end
    i = 0
    while i < len(label) and label[i].isdigit():
        i += 1
    
    if i > 0:
        order_index = int(label[:i])
        part_label = label[i:].strip(".")
    
    return order_index, part_label

def save_multiple_cropped_images(images: List[Image.Image], save_dir: str, prefix: str = "") -> List[str]:
    """Save multiple cropped PIL Images and return list of file paths"""
    image_paths = []
    
    for i, image in enumerate(images, 1):
        # Generate unique filename for each image
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}_img{i}_{timestamp}_{unique_id}.png"
        
        # Ensure directory exists
        os.makedirs(save_dir, exist_ok=True)
        
        # Save image
        file_path = os.path.join(save_dir, filename)
        image.save(file_path, "PNG")
        image_paths.append(file_path)
    
    return image_paths
