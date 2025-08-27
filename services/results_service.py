# services/results_service.py
import os
import sys
import json
from typing import Dict, Any, Optional

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.manager_v2 import db_manager
from core.utils import format_question_label

class ResultsService:
    """
    Service layer for fetching and processing data for the results page.
    """

    @staticmethod
    def get_results_for_submission(submission_id: int) -> Optional[Dict[str, Any]]:
        """
        Fetches all necessary data for a single submission's results page
        using a single, efficient, eagerly-loaded query.
        """
        submission = db_manager.get_submission_by_id(submission_id)
        if not submission:
            return None

        graded_items_data = []
        for item in submission.items:
            if item.grading:
                grading = item.grading
                question = item.question

                error_phrases = []
                if grading.error_phrases:
                    try:
                        loaded_phrases = json.loads(grading.error_phrases)
                        if isinstance(loaded_phrases, list):
                            error_phrases = loaded_phrases
                    except (json.JSONDecodeError, TypeError):
                        pass

                graded_items_data.append({
                    "source_page_index": item.source_page_index,
                    "question_label": format_question_label(question.order_index, question.part_label),
                    "is_correct": grading.is_correct,
                    "confidence": grading.confidence,
                    "error_description": grading.error_description,
                    "partial_credit": grading.partial_credit,
                    "error_phrases": error_phrases,
                })
        
        image_paths = []
        if submission.original_image_paths:
            try:
                loaded_paths = json.loads(submission.original_image_paths)
                if isinstance(loaded_paths, list):
                    image_paths = loaded_paths
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "student_name": submission.student_name,
            "exam_name": submission.exam.name if submission.exam else "Unknown Exam",
            "submission_image_paths": image_paths,
            "graded_items": sorted(graded_items_data, key=lambda x: x['question_label'])
        }

# Create a single global instance for easy access
results_service = ResultsService()