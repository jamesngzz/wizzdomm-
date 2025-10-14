# services/image_service.py
import os
import sys
from typing import List, Tuple
from PIL import Image

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from core.utils import (
    save_cropped_image,
    save_multiple_cropped_images,
    save_uploaded_image,
    save_uploaded_file,
    validate_image_file,
    is_pdf_file
)
from core.config import QUESTIONS_DIR, ANSWERS_DIR, EXAMS_DIR, SUBMISSIONS_DIR

class ImageService:
    """Service layer for all file processing and storage operations (images and PDFs)."""

    @staticmethod
    def save_question_images(
        images: List[Image.Image],
        order_index: int,
        part_label: str
    ) -> Tuple[bool, str, List[str]]:
        """Saves cropped question images to the filesystem."""
        try:
            prefix = f"q_{order_index}_{part_label}"
            if len(images) == 1:
                path = save_cropped_image(images[0], QUESTIONS_DIR, prefix)
                return True, "Image saved.", [path]
            else:
                paths = save_multiple_cropped_images(images, QUESTIONS_DIR, prefix)
                return True, f"{len(paths)} images saved.", paths
        except Exception as e:
            return False, f"Error saving question images: {str(e)}", []

    @staticmethod
    def save_answer_images(
        images: List[Image.Image],
        order_index: int,
        part_label: str,
        student_name: str
    ) -> Tuple[bool, str, List[str]]:
        """Saves cropped answer images to the filesystem."""
        try:
            student_prefix = student_name.strip().replace(' ', '_')
            prefix = f"ans_{order_index}_{part_label}_{student_prefix}"
            if len(images) == 1:
                path = save_cropped_image(images[0], ANSWERS_DIR, prefix)
                return True, "Image saved.", [path]
            else:
                paths = save_multiple_cropped_images(images, ANSWERS_DIR, prefix)
                return True, f"{len(paths)} images saved.", paths
        except Exception as e:
            return False, f"Error saving answer images: {str(e)}", []

    @staticmethod
    def save_uploaded_images(
        uploaded_files: List,
        save_dir: str,
        filename_prefix: str
    ) -> Tuple[bool, str, List[str]]:
        """Validates and saves a list of uploaded files (images or PDFs)."""
        if not uploaded_files:
            return False, "No files were provided.", []

        all_image_paths = []
        errors = []
        pdf_count = 0
        image_count = 0

        for up_file in uploaded_files:
            # Use new save_uploaded_file function that handles both images and PDFs
            success, msg, file_paths = save_uploaded_file(up_file, save_dir, filename_prefix)

            if not success:
                errors.append(f"{up_file.name}: {msg}")
                continue

            all_image_paths.extend(file_paths)

            # Track file types for better messaging
            if is_pdf_file(up_file):
                pdf_count += 1
            else:
                image_count += 1

        if errors:
            error_msg = "Some files failed: " + "; ".join(errors)
            if all_image_paths:
                return False, error_msg, all_image_paths
            else:
                return False, error_msg, []

        # Create success message
        success_parts = []
        if image_count > 0:
            success_parts.append(f"{image_count} ảnh")
        if pdf_count > 0:
            success_parts.append(f"{pdf_count} PDF")

        file_desc = " và ".join(success_parts)
        total_images = len(all_image_paths)
        success_msg = f"Đã lưu {file_desc}, tạo ra {total_images} trang ảnh."

        return True, success_msg, all_image_paths

    @staticmethod
    def save_uploaded_exam_images(
        uploaded_files: List, exam_name: str
    ) -> Tuple[bool, str, List[str]]:
        """Saves uploaded exam images."""
        prefix = f"exam_{exam_name.strip().replace(' ', '_')}"
        return ImageService.save_uploaded_images(uploaded_files, EXAMS_DIR, prefix)

    @staticmethod
    def save_uploaded_submission_images(
        uploaded_files: List, student_name: str
    ) -> Tuple[bool, str, List[str]]:
        """Saves uploaded submission images."""
        prefix = f"sub_{student_name.strip().replace(' ', '_')}"
        return ImageService.save_uploaded_images(uploaded_files, SUBMISSIONS_DIR, prefix)