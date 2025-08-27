# services/submission_service.py
import os
import sys
from typing import List, Tuple, Optional
from PIL import Image

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.manager_v2 import db_manager
from .image_service import ImageService

class SubmissionService:
    """Service layer for submission-related business logic."""

    @staticmethod
    def _validate_submission_data(exam_id: int, student_name: str, uploaded_files: List) -> str:
        """Validates input data for submission creation, returning an error message string."""
        if not student_name or not student_name.strip():
            return "Student name is required."
        if not uploaded_files:
            return "At least one answer sheet image is required."
        exam = db_manager.get_exam_by_id(exam_id)
        if not exam:
            return f"Exam with ID {exam_id} not found."
        if not exam.questions:
            return "The selected exam has no digitized questions. Please digitize it first."
        return ""

    @staticmethod
    def create_submission(
        exam_id: int,
        student_name: str,
        uploaded_files: List
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Creates a new submission with validation and image processing.
        """
        try:
            error_message = SubmissionService._validate_submission_data(exam_id, student_name, uploaded_files)
            if error_message:
                return False, error_message, None

            img_success, img_message, image_paths = ImageService.save_uploaded_submission_images(
                uploaded_files, student_name
            )
            if not img_success:
                return False, f"Failed to save images: {img_message}", None

            submission_id = db_manager.create_submission(
                exam_id=exam_id,
                student_name=student_name.strip(),
                original_image_paths=image_paths
            )

            if submission_id:
                return True, f"Submission for {student_name.strip()} created successfully.", submission_id
            else:
                return False, "Failed to save submission to the database.", None
        except Exception as e:
            return False, f"An unexpected error occurred: {str(e)}", None

    @staticmethod
    def create_answer_mapping(
        submission_id: int,
        question_id: int,
        cropped_images: List[Image.Image],
        student_name: str,
        source_page_index: int
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Creates a mapping between a question and a cropped answer image.
        """
        if not cropped_images:
            return False, "At least one cropped answer image is required.", None

        try:
            question = db_manager.get_question_by_id(question_id)
            if not question:
                return False, "Associated question not found.", None

            # Check if submission item already exists
            existing_item = db_manager.find_submission_item(submission_id, question_id)
            
            if existing_item:
                # Add images to existing submission item
                img_success, img_message, image_paths = ImageService.save_answer_images(
                    images=cropped_images,
                    order_index=question.order_index,
                    part_label=question.part_label,
                    student_name=student_name
                )
                if not img_success:
                    return False, f"Failed to save answer image: {img_message}", None
                
                # Update existing item with new images
                update_success = db_manager.update_submission_item_images(submission_id, question_id, image_paths)
                if update_success:
                    return True, f"Added images to answer for question {question.part_label}.", existing_item.id
                else:
                    return False, "Failed to update answer with new images.", None
            else:
                # Create new submission item
                img_success, img_message, image_paths = ImageService.save_answer_images(
                    images=cropped_images,
                    order_index=question.order_index,
                    part_label=question.part_label,
                    student_name=student_name
                )
                if not img_success:
                    return False, f"Failed to save answer image: {img_message}", None

                item_id = db_manager.create_submission_item(
                    submission_id=submission_id,
                    question_id=question_id,
                    answer_image_path=image_paths[0],
                    source_page_index=source_page_index,
                    answer_image_paths=image_paths if len(image_paths) > 1 else None,
                    has_multiple_images=len(image_paths) > 1
                )
                
                if item_id:
                    return True, "Answer mapped successfully.", item_id
                else:
                    return False, "Failed to save the answer mapping to the database.", None
        except Exception as e:
            return False, f"An unexpected error occurred: {str(e)}", None
    
    @staticmethod
    def get_all_submissions_with_answers() -> Tuple[bool, str, List[dict]]:
        """
        Gets all submissions that have at least one mapped answer, making them ready for grading.
        """
        try:
            all_submissions = db_manager.get_all_submissions()
            submissions_with_answers = []
            for submission in all_submissions:
                if submission.items:
                    exam = submission.exam
                    submissions_with_answers.append({
                        "submission": submission,
                        "items": submission.items,
                        "exam_name": exam.name if exam else "Unknown Exam"
                    })
            return True, f"Found {len(submissions_with_answers)} submissions ready for grading.", submissions_with_answers
        except Exception as e:
            return False, f"Error retrieving submissions: {str(e)}", []
    
    @staticmethod
    def get_submission_progress(submission_id: int) -> Tuple[bool, str, Optional[dict]]:
        """
        Retrieves progress details for a single submission (mapping and grading status).
        """
        try:
            submission = db_manager.get_submission_by_id(submission_id)
            if not submission:
                return False, "Submission not found.", None
            
            exam = submission.exam
            total_questions = len(exam.questions) if exam else 0
            
            progress = {
                "submission_id": submission.id,
                "student_name": submission.student_name,
                "submission": submission,
                "items": submission.items,
                "total_questions": total_questions,
                "mapped_answers": len(submission.items),
                "graded_answers": len(db_manager.get_gradings_by_submission(submission.id))
            }
            return True, "Progress retrieved.", progress
        except Exception as e:
            return False, f"Error calculating progress: {str(e)}", None