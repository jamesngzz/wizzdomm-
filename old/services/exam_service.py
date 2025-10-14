# services/exam_service.py
import os
import sys
from typing import List, Dict, Any, Optional, Tuple

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.manager_v2 import db_manager

class ExamService:
    """Service layer for exam-related business logic."""

    @staticmethod
    def _validate_exam_data(name: str, topic: str, image_paths: List[str]) -> List[str]:
        """Validates input data for exam creation."""
        errors = []
        if not name or not name.strip():
            errors.append("Exam name is required.")
        if not topic or not topic.strip():
            errors.append("Topic is required.")
        if not image_paths:
            errors.append("At least one exam image is required.")
        return errors

    @staticmethod
    def create_exam(
        name: str,
        topic: str,
        grade_level: str,
        image_paths: List[str]
    ) -> Tuple[bool, str, Optional[int]]:
        """
        Creates a new exam after validating inputs.

        Args:
            name: The name of the exam.
            topic: The topic of the exam.
            grade_level: The grade level for the exam.
            image_paths: A list of file paths to the original exam images.

        Returns:
            A tuple of (success, message, exam_id).
        """
        try:
            validation_errors = ExamService._validate_exam_data(name, topic, image_paths)
            if validation_errors:
                return False, " ".join(validation_errors), None

            exam_id = db_manager.create_exam(
                title=name.strip(),
                topic=topic.strip(),
                grade_level=grade_level,
                original_image_paths=image_paths
            )

            if exam_id:
                return True, f"Exam '{name.strip()}' created successfully with ID: {exam_id}", exam_id
            else:
                return False, "Failed to save the exam to the database.", None

        except Exception as e:
            return False, f"An unexpected error occurred: {str(e)}", None

    @staticmethod
    def get_exam_list() -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Retrieves a list of all exams with summary information.

        Returns:
            A tuple of (success, message, exam_list).
        """
        try:
            exams = db_manager.list_exams()
            return True, "Exams retrieved successfully.", exams
        except Exception as e:
            return False, f"Error retrieving exams: {str(e)}", []

    @staticmethod
    def get_exam_details(exam_id: int) -> Tuple[bool, str, Optional[Any]]:
        """
        Retrieves detailed information for a single exam by its ID.

        Args:
            exam_id: The ID of the exam.

        Returns:
            A tuple of (success, message, exam_object).
        """
        try:
            exam = db_manager.get_exam_by_id(exam_id)
            if exam:
                return True, "Exam details retrieved successfully.", exam
            else:
                return False, f"Exam with ID {exam_id} not found.", None
        except Exception as e:
            return False, f"Error retrieving exam details: {str(e)}", None