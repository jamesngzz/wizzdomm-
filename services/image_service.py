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
    validate_image_file
)
from core.config import QUESTIONS_DIR, ANSWERS_DIR, EXAMS_DIR, SUBMISSIONS_DIR

class ImageService:
    """Service layer for all image processing and file storage operations."""

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
        """Validates and saves a list of uploaded files."""
        if not uploaded_files:
            return False, "No files were provided.", []

        saved_paths = []
        errors = []
        for up_file in uploaded_files:
            is_valid, msg = validate_image_file(up_file)
            if not is_valid:
                errors.append(f"{up_file.name}: {msg}")
                continue
            try:
                path = save_uploaded_image(up_file, save_dir, filename_prefix)
                saved_paths.append(path)
            except Exception as e:
                errors.append(f"Could not save {up_file.name}: {e}")

        if errors:
            return False, " ".join(errors), saved_paths
        
        return True, f"Successfully saved {len(saved_paths)} images.", saved_paths

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