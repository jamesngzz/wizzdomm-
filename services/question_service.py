# services/question_service.py
import os
import sys
from typing import List, Tuple, Optional, Any
from PIL import Image

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.manager_v2 import db_manager
from .image_service import ImageService
from core.utils import parse_question_label, format_question_label

class QuestionService:
    """Service layer for question-related business logic."""

    @staticmethod
    def create_question(
        exam_id: int,
        question_label: str,
        cropped_images: List[Image.Image],
        replace_if_exists: bool = True # Defaulting to True for simplicity in UI
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Creates or updates a question with validation and image processing.

        Args:
            exam_id: The ID of the parent exam.
            question_label: The label for the question (e.g., "1a", "2b").
            cropped_images: A list of cropped PIL Images for the question.
            replace_if_exists: Whether to overwrite an existing question with the same label.

        Returns:
            A tuple of (success, message, question_id).
        """
        if not question_label.strip() or not cropped_images:
            return False, "Question label and at least one image are required.", None

        try:
            order_index, part_label = parse_question_label(question_label)
            formatted_label = format_question_label(order_index, part_label)

            # Check if question with same order_index + part_label already exists
            existing_question = db_manager.find_question_by_label(exam_id, order_index, part_label)
            
            if existing_question:
                # Add images to existing question
                img_success, img_message, image_paths = ImageService.save_question_images(
                    images=cropped_images,
                    order_index=order_index,
                    part_label=part_label
                )
                if not img_success:
                    return False, f"Failed to save images: {img_message}", None
                
                # Update existing question with new images
                update_success = db_manager.update_question_images(existing_question.id, image_paths)
                if update_success:
                    return True, f"Added images to existing question {formatted_label}.", existing_question.id
                else:
                    return False, "Failed to update question with new images.", None
            else:
                # Create new question
                img_success, img_message, image_paths = ImageService.save_question_images(
                    images=cropped_images,
                    order_index=order_index,
                    part_label=part_label
                )
                if not img_success:
                    return False, f"Failed to save images: {img_message}", None

                question_id = db_manager.create_question(
                    exam_id=exam_id,
                    question_image_path=image_paths[0],
                    question_image_paths=image_paths if len(image_paths) > 1 else None,
                    has_multiple_images=len(image_paths) > 1,
                    order_index=order_index,
                    part_label=part_label
                )

                if question_id:
                    return True, f"Successfully created question {formatted_label}.", question_id
                else:
                    return False, "Failed to save question to the database.", None

        except Exception as e:
            return False, f"An unexpected error occurred: {str(e)}", None

    @staticmethod
    def get_questions_by_exam(exam_id: int) -> Tuple[bool, str, List[Any]]:
        """Retrieves all questions for a given exam, ordered correctly."""
        try:
            questions = db_manager.get_questions_by_exam(exam_id)
            return True, f"Retrieved {len(questions)} questions.", questions
        except Exception as e:
            return False, f"Error retrieving questions: {str(e)}", []
            
    @staticmethod
    def get_question_by_id(question_id: int) -> Tuple[bool, str, Optional[Any]]:
        """Retrieves a single question by its ID."""
        try:
            question = db_manager.get_question_by_id(question_id)
            if question:
                return True, "Question found.", question
            else:
                return False, f"Question with ID {question_id} not found.", None
        except Exception as e:
            return False, f"Error retrieving question: {str(e)}", None

    @staticmethod
    def delete_question(question_id: int) -> Tuple[bool, str, Optional[int]]:
        """
        Deletes a question and all its associated data (answers, grades, images).
        """
        try:
            question = db_manager.get_question_by_id(question_id)
            if not question:
                return False, f"Question with ID {question_id} not found.", None
            
            label = format_question_label(question.order_index, question.part_label)
            
            # The database manager now handles the cascading delete and file cleanup
            success = db_manager.delete_question(question_id)
            
            if success:
                return True, f"Successfully deleted question {label}.", question_id
            else:
                return False, f"Failed to delete question {label} from the database.", None
        except Exception as e:
            return False, f"An error occurred during deletion: {str(e)}", None