# services/grading_service.py
import os
import sys
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.manager_v2 import db_manager
from core.ai_models import get_ai_model
from core.utils import format_question_label

logger = logging.getLogger(__name__)

class GradingService:
    """
    Service layer for all grading-related business logic.
    It uses a generic AI model interface and communicates with the database manager.
    """

    def __init__(self, ai_model=None):
        self.ai_model = ai_model or get_ai_model()

    def _prepare_image_paths(self, db_object, path_attribute, paths_attribute, has_multiple_attribute) -> List[str]:
        """Helper to consolidate ALL images: primary + additional paths from database object."""
        all_paths = []
        
        # Always include primary image if exists
        primary_path = getattr(db_object, path_attribute, None)
        if primary_path:
            all_paths.append(primary_path)
        
        # Add additional images from JSON paths if they exist
        additional_paths_json = getattr(db_object, paths_attribute, None)
        if additional_paths_json:
            try:
                loaded_paths = json.loads(additional_paths_json)
                if loaded_paths:
                    all_paths.extend(loaded_paths)
            except (json.JSONDecodeError, TypeError):
                pass  # Skip invalid JSON, keep primary only
        
        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in all_paths:
            if path and path not in seen:
                seen.add(path)
                unique_paths.append(path)
        
        # Final check to ensure all returned paths actually exist on the filesystem
        return [p for p in unique_paths if os.path.exists(p)]

    def grade_single_question(self, submission_item_id: int, clarify: str = None) -> Tuple[bool, str, Optional[int]]:
        """
        Grades a single submission item using the configured Vision AI model.
        """
        try:
            item = db_manager.get_submission_item_by_id(submission_item_id)
            if not item:
                return False, f"Submission Item ID {submission_item_id} not found.", None
            
            question = item.question
            if not question:
                 return False, f"Question for item ID {submission_item_id} not found.", None

            question_paths = self._prepare_image_paths(question, 'question_image_path', 'question_image_paths', 'has_multiple_images')
            answer_paths = self._prepare_image_paths(item, 'answer_image_path', 'answer_image_paths', 'has_multiple_images')

            if not question_paths:
                return False, "Could not find the question image(s) on disk.", None
            if not answer_paths:
                return False, "Could not find the student's answer image(s) on disk.", None

            # Get previous grading if clarify is provided (for re-grading)
            previous_grading = None
            if clarify:
                existing_grading = getattr(item, 'grading', None)
                if existing_grading:
                    previous_grading = {
                        'is_correct': existing_grading.is_correct,
                        'error_description': existing_grading.error_description,
                        'error_phrases': existing_grading.error_phrases,
                        'partial_credit': existing_grading.partial_credit
                    }

            # Log input images being sent to LLM
            logger.info(f"Calling LLM for submission_item {item.id}:")
            logger.info(f"  Question images ({len(question_paths)}): {[os.path.basename(p) for p in question_paths]}")
            logger.info(f"  Answer images ({len(answer_paths)}): {[os.path.basename(p) for p in answer_paths]}")
            logger.info(f"  Question paths: {question_paths}")
            logger.info(f"  Answer paths: {answer_paths}")
            if clarify:
                logger.info(f"  Clarify text: {clarify}")
                logger.info(f"  Previous grading: {previous_grading}")

            start_time = datetime.now()
            ai_result = self.ai_model.grade_image_pair(question_paths, answer_paths, clarify=clarify, previous_grading=previous_grading)
            processing_time = (datetime.now() - start_time).total_seconds()
            
            logger.info(f"AI grading for item {item.id} completed in {processing_time:.2f}s.")

            # Handle both new and legacy error formats
            critical_errors = ai_result.get('critical_errors', [])
            part_errors = ai_result.get('part_errors', [])

            # Legacy support: if old format is present, convert to new format
            if ai_result.get('error_description') and not critical_errors and not part_errors:
                # Convert legacy error_description to critical_errors for backward compatibility
                legacy_error = {
                    "description": ai_result.get('error_description', ''),
                    "phrases": ai_result.get('error_phrases', [])
                }
                critical_errors = [legacy_error] if legacy_error["description"] else []

            grading_id = db_manager.create_grading(
                submission_item_id=item.id,
                question_id=question.id,
                is_correct=ai_result.get('is_correct', False),
                error_description=ai_result.get('error_description'),  # Keep for backward compatibility
                error_phrases=ai_result.get('error_phrases', []),  # Keep for backward compatibility
                critical_errors=critical_errors,
                part_errors=part_errors,
                partial_credit=ai_result.get('partial_credit', False),
                clarify_notes=clarify
            )

            if grading_id:
                label = format_question_label(question.order_index, question.part_label)
                return True, f"Successfully graded question {label}.", grading_id
            else:
                return False, "Failed to save grading result to the database.", None

        except Exception as e:
            logger.error(f"Error in grade_single_question for item {submission_item_id}: {e}")
            return False, f"An unexpected error occurred during grading: {e}", None

    def grade_submission_batch(self, submission_id: int, force_regrade: bool = False) -> Tuple[bool, str, Dict]:
        """
        Grades all applicable items in a submission as a batch.
        """
        items = db_manager.get_submission_items(submission_id)
        
        items_to_grade = []
        for item in items:
            if force_regrade or not item.grading:
                question = item.question
                question_paths = self._prepare_image_paths(question, 'question_image_path', 'question_image_paths', 'has_multiple_images')
                answer_paths = self._prepare_image_paths(item, 'answer_image_path', 'answer_image_paths', 'has_multiple_images')

                if question_paths and answer_paths:
                    items_to_grade.append({
                        "submission_item_id": item.id,
                        "question_id": question.id,
                        "question_image_paths": question_paths,
                        "answer_image_paths": answer_paths
                    })

        if not items_to_grade:
            return True, "All items are already graded.", {"graded_count": 0}

        try:
            # The base model's default is a simple loop. A more advanced model implementation
            # (e.g., using an OpenAI batching endpoint) could override this in the model class.
            ai_results = self.ai_model.grade_batch(items_to_grade)

            graded_count = 0
            for item_data, result_data in zip(items_to_grade, ai_results):
                # Handle both new and legacy error formats
                critical_errors = result_data.get('critical_errors', [])
                part_errors = result_data.get('part_errors', [])

                # Legacy support: if old format is present, convert to new format
                if result_data.get('error_description') and not critical_errors and not part_errors:
                    legacy_error = {
                        "description": result_data.get('error_description', ''),
                        "phrases": result_data.get('error_phrases', [])
                    }
                    critical_errors = [legacy_error] if legacy_error["description"] else []

                db_manager.create_grading(
                    submission_item_id=item_data['submission_item_id'],
                    question_id=item_data['question_id'],
                    is_correct=result_data.get('is_correct', False),
                    error_description=result_data.get('error_description'),  # Keep for backward compatibility
                    error_phrases=result_data.get('error_phrases', []),  # Keep for backward compatibility
                    critical_errors=critical_errors,
                    part_errors=part_errors,
                    partial_credit=result_data.get('partial_credit', False)
                )
                graded_count += 1
            
            summary = {"graded_count": graded_count, "total_items_processed": len(items_to_grade)}
            return True, f"Batch grading complete. Graded {graded_count} items.", summary

        except Exception as e:
            logger.error(f"Error in grade_submission_batch for submission {submission_id}: {e}")
            return False, f"An unexpected error occurred during batch grading: {e}", {}

# Create a single global instance for easy access from pages
grading_service = GradingService()