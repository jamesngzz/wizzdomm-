import os
import uuid
from datetime import datetime
from PIL import Image
from typing import List, Tuple
import streamlit as st

from .config import QUESTIONS_DIR, ANSWERS_DIR, SUPPORTED_IMAGE_FORMATS, SUPPORTED_FILE_FORMATS, MAX_IMAGE_SIZE_MB, MAX_PDF_SIZE_MB

# PDF processing imports (with fallback)
try:
    from pdf2image import convert_from_path, convert_from_bytes
    from PyPDF2 import PdfReader
    PDF_SUPPORT = True
except ImportError:
    PDF_SUPPORT = False

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
        st.image(image_path, caption=caption)
        
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

def is_pdf_file(uploaded_file) -> bool:
    """Check if uploaded file is a PDF"""
    if uploaded_file is None:
        return False
    return uploaded_file.name.lower().endswith('.pdf')

def validate_pdf_file(uploaded_file) -> Tuple[bool, str]:
    """Validate uploaded PDF file"""
    if uploaded_file is None:
        return False, "No file uploaded"

    # Check file extension
    if not is_pdf_file(uploaded_file):
        return False, "File must be a PDF"

    # Check file size
    file_size_mb = uploaded_file.size / (1024 * 1024)
    if file_size_mb > MAX_PDF_SIZE_MB:
        return False, f"PDF file too large. Maximum size: {MAX_PDF_SIZE_MB}MB"

    # Check if PDF processing is available
    if not PDF_SUPPORT:
        return False, "PDF processing libraries not available"

    return True, "Valid PDF file"

def convert_pdf_to_images(pdf_path: str, dpi: int = 200) -> Tuple[bool, str, List[str]]:
    """
    Convert PDF file to list of PNG images.

    Args:
        pdf_path: Path to PDF file
        dpi: Resolution for conversion (higher = better quality)

    Returns:
        Tuple of (success, message, list_of_image_paths)
    """
    if not PDF_SUPPORT:
        return False, "PDF processing libraries not available", []

    if not os.path.exists(pdf_path):
        return False, f"PDF file not found: {pdf_path}", []

    try:
        # Convert PDF to images
        images = convert_from_path(pdf_path, dpi=dpi, fmt='PNG')

        if not images:
            return False, "No pages found in PDF", []

        # Save images to disk
        image_paths = []
        pdf_basename = os.path.splitext(os.path.basename(pdf_path))[0]
        pdf_dir = os.path.dirname(pdf_path)

        for i, image in enumerate(images):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]
            image_filename = f"{pdf_basename}_page{i+1}_{timestamp}_{unique_id}.png"
            image_path = os.path.join(pdf_dir, image_filename)

            image.save(image_path, "PNG")
            image_paths.append(image_path)

        return True, f"Converted PDF to {len(images)} images", image_paths

    except Exception as e:
        return False, f"Failed to convert PDF: {str(e)}", []

def convert_uploaded_pdf_to_images(uploaded_file, save_dir: str, prefix: str = "") -> Tuple[bool, str, List[str]]:
    """
    Convert uploaded PDF file to images.

    Args:
        uploaded_file: Streamlit uploaded file object
        save_dir: Directory to save converted images
        prefix: Filename prefix

    Returns:
        Tuple of (success, message, list_of_image_paths)
    """
    if not PDF_SUPPORT:
        return False, "PDF processing libraries not available", []

    # Validate PDF first
    is_valid, msg = validate_pdf_file(uploaded_file)
    if not is_valid:
        return False, msg, []

    try:
        # Convert PDF bytes to images
        pdf_bytes = uploaded_file.getvalue()
        images = convert_from_bytes(pdf_bytes, dpi=200, fmt='PNG')

        if not images:
            return False, "No pages found in PDF", []

        # Ensure directory exists
        os.makedirs(save_dir, exist_ok=True)

        # Save images to disk
        image_paths = []

        for i, image in enumerate(images):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            unique_id = str(uuid.uuid4())[:8]

            if prefix:
                filename = f"{prefix}_page{i+1}_{timestamp}_{unique_id}.png"
            else:
                filename = f"pdf_page{i+1}_{timestamp}_{unique_id}.png"

            image_path = os.path.join(save_dir, filename)
            image.save(image_path, "PNG")
            image_paths.append(image_path)

        return True, f"Converted PDF to {len(images)} images", image_paths

    except Exception as e:
        return False, f"Failed to convert PDF: {str(e)}", []

def save_uploaded_file(uploaded_file, save_dir: str, prefix: str = "") -> Tuple[bool, str, List[str]]:
    """
    Save uploaded file (image or PDF) and return image paths.
    PDFs are automatically converted to images.

    Args:
        uploaded_file: Streamlit uploaded file object
        save_dir: Directory to save files
        prefix: Filename prefix

    Returns:
        Tuple of (success, message, list_of_image_paths)
    """
    if uploaded_file is None:
        return False, "No file uploaded", []

    # Handle PDF files
    if is_pdf_file(uploaded_file):
        return convert_uploaded_pdf_to_images(uploaded_file, save_dir, prefix)

    # Handle image files (existing logic)
    is_valid, msg = validate_image_file(uploaded_file)
    if not is_valid:
        return False, msg, []

    try:
        # Save single image
        image_path = save_uploaded_image(uploaded_file, save_dir, prefix)
        return True, "Image saved", [image_path]
    except Exception as e:
        return False, f"Failed to save image: {str(e)}", []
