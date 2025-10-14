from __future__ import annotations

from typing import Dict, Any, Optional
from .models import SubmissionItem, Grading
from apps.common.files import normalized_path_exists
from apps.grading.gemini import GeminiGrader


def simple_grade_logic(item: SubmissionItem, clarify: Optional[str] = None) -> Dict[str, Any]:
    try:
        grader = GeminiGrader()
        q_paths = item.question.question_image_paths or []
        a_paths = item.answer_image_paths or []

        # Validate that we have the required images
        if not q_paths:
            raise ValueError("No question images found")
        if not a_paths:
            raise ValueError("No answer images found")

        # Check if image files exist
        for path in q_paths + a_paths:
            if not normalized_path_exists(path):
                raise FileNotFoundError(f"Image file not found: {path}")

        previous = None
        try:
            if item.grading:
                previous = {
                    "is_correct": item.grading.is_correct,
                    "error_description": item.grading.error_description,
                    "error_phrases": item.grading.error_phrases,
                    "partial_credit": item.grading.partial_credit,
                }
        except:
            # No grading exists yet, which is fine
            previous = None

        solution = None
        if item.question.solution_steps:
            try:
                steps = item.question.solution_steps
                solution = {"steps": steps}
            except Exception:
                solution = None

        result = grader.grade_image_pair(q_paths, a_paths, clarify=clarify, previous_grading=previous, solution=solution)
        
        # Validate the result structure
        if not isinstance(result, dict):
            raise ValueError("Invalid result format from grader")
        
        # Ensure required fields exist
        if "is_correct" not in result:
            raise ValueError("Missing 'is_correct' field in result")
        
        return result
        
    except ValueError as e:
        # Validation errors - these are user/system issues, not API issues
        return {
            "is_correct": False,
            "critical_errors": [{"description": f"Validation error: {str(e)}", "phrases": ["validation error"]}],
            "part_errors": [],
            "partial_credit": False,
        }
    except FileNotFoundError as e:
        # File not found errors
        return {
            "is_correct": False,
            "critical_errors": [{"description": f"File error: {str(e)}", "phrases": ["file missing"]}],
            "part_errors": [],
            "partial_credit": False,
        }
    except Exception as e:
        # API or other unexpected errors
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Grading failed for item {item.id}: {str(e)}", exc_info=True)
        
        return {
            "is_correct": False,
            "critical_errors": [{"description": f"Grading service error: {str(e)}", "phrases": ["service error"]}],
            "part_errors": [],
            "partial_credit": False,
        }


def grade_item_and_persist(item: SubmissionItem, clarify: Optional[str] = None) -> int:
    result = simple_grade_logic(item, clarify=clarify)
    grading, _created = Grading.objects.get_or_create(
        submission_item=item,
        defaults={
            "question": item.question,
            "is_correct": result["is_correct"],
            "critical_errors": result.get("critical_errors", []),
            "part_errors": result.get("part_errors", []),
            "partial_credit": result.get("partial_credit", False),
            "clarify_notes": clarify,
        },
    )

    if not _created:
        grading.is_correct = result["is_correct"]
        grading.critical_errors = result.get("critical_errors", [])
        grading.part_errors = result.get("part_errors", [])
        grading.partial_credit = result.get("partial_credit", False)
        grading.clarify_notes = clarify
        grading.save()

    return grading.id


