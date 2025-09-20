import os
import sys
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.manager_v2 import db_manager
from core.ai_models.openai_solver import OpenAISolver
from core.config import OPENAI_API_KEY, OPENAI_SOLVER_MODEL

logger = logging.getLogger(__name__)

class QuestionSolverService:
    """
    Service layer for AI-powered question solving using OpenAI GPT-5 Mini.
    Handles batch processing, database updates, and error management.
    """

    def __init__(self, openai_api_key: str = None):
        self.openai_api_key = openai_api_key or OPENAI_API_KEY
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required for question solving")

        self.solver = OpenAISolver(api_key=self.openai_api_key, model_name=OPENAI_SOLVER_MODEL)
        logger.info("QuestionSolverService initialized")

    def _prepare_question_image_paths(self, question) -> List[str]:
        """Prepare all image paths for a question (primary + additional)."""
        all_paths = []

        # Add primary image path
        if question.question_image_path:
            all_paths.append(question.question_image_path)

        # Add additional image paths from JSON
        if question.question_image_paths:
            try:
                additional_paths = json.loads(question.question_image_paths)
                if additional_paths:
                    all_paths.extend(additional_paths)
            except (json.JSONDecodeError, TypeError):
                logger.warning(f"Invalid JSON in question_image_paths for question {question.id}")

        # Remove duplicates while preserving order
        seen = set()
        unique_paths = []
        for path in all_paths:
            if path not in seen:
                seen.add(path)
                unique_paths.append(path)

        return unique_paths

    async def solve_single_question(self, question_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Solve a single question and update the database.

        Args:
            question_id: ID of the question to solve

        Returns:
            Tuple of (success, message, solution_data)
        """
        try:
            # Get question from database
            question = db_manager.get_question_by_id(question_id)
            if not question:
                return False, f"Question with ID {question_id} not found", None

            # Check if already has verified solution
            if question.solution_verified:
                return False, "Question already has a verified solution", None

            # Prepare image paths
            image_paths = self._prepare_question_image_paths(question)
            if not image_paths:
                return False, "No valid image paths found for question", None

            # Verify all image files exist
            missing_images = [path for path in image_paths if not os.path.exists(path)]
            if missing_images:
                return False, f"Missing image files: {missing_images}", None

            logger.info(f"Solving question {question_id} with images: {[os.path.basename(p) for p in image_paths]}")

            # Solve the question
            solution = await self.solver.solve_question(image_paths)

            # Check for errors in solution
            if solution.get('error'):
                return False, f"AI solving failed: {solution.get('explanation', 'Unknown error')}", solution

            # Update database with solution
            success = db_manager.update_question_solution(
                question_id=question_id,
                solution_answer=solution.get('answer', ''),
                solution_steps=json.dumps(solution.get('steps', []), ensure_ascii=False),
                solution_points=json.dumps([step.get('points', 0) for step in solution.get('steps', [])], ensure_ascii=False),
                solution_verified=False,  # Requires teacher approval
                solution_generated_at=datetime.now()
            )

            if success:
                logger.info(f"Successfully solved and saved solution for question {question_id}")
                return True, "Question solved successfully", solution
            else:
                return False, "Failed to save solution to database", solution

        except Exception as e:
            logger.error(f"Error solving question {question_id}: {e}")
            return False, f"Error solving question: {str(e)}", None

    async def solve_questions_batch(self, question_ids: List[int]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Solve multiple questions in batch with concurrent processing.

        Args:
            question_ids: List of question IDs to solve

        Returns:
            Tuple of (success, message, results_summary)
        """
        if not question_ids:
            return False, "No question IDs provided", {}

        logger.info(f"Starting batch solving for {len(question_ids)} questions")

        # Prepare questions data for batch processing
        questions_data = []
        questions_map = {}

        for question_id in question_ids:
            question = db_manager.get_question_by_id(question_id)
            if not question:
                logger.warning(f"Question {question_id} not found, skipping")
                continue

            # Skip already verified solutions
            if question.solution_verified:
                logger.info(f"Question {question_id} already has verified solution, skipping")
                continue

            image_paths = self._prepare_question_image_paths(question)
            if not image_paths:
                logger.warning(f"No valid images for question {question_id}, skipping")
                continue

            questions_data.append({
                'question_id': question_id,
                'image_paths': image_paths
            })
            questions_map[question_id] = question

        if not questions_data:
            return False, "No valid questions to solve", {}

        try:
            # Solve all questions concurrently
            solutions = await self.solver.solve_questions_batch(questions_data)

            # Process results and update database
            successful_saves = 0
            failed_saves = 0
            solution_errors = 0
            results_summary = {
                'total_attempted': len(solutions),
                'successful_solutions': 0,
                'failed_solutions': 0,
                'database_errors': 0,
                'details': []
            }

            for solution in solutions:
                question_id = solution['question_id']

                try:
                    # Check for AI solution errors
                    if solution.get('error'):
                        solution_errors += 1
                        results_summary['details'].append({
                            'question_id': question_id,
                            'status': 'ai_error',
                            'message': solution.get('explanation', 'Unknown AI error')
                        })
                        continue

                    # Save to database
                    success = db_manager.update_question_solution(
                        question_id=question_id,
                        solution_answer=solution.get('answer', ''),
                        solution_steps=json.dumps(solution.get('steps', []), ensure_ascii=False),
                        solution_points=json.dumps([step.get('points', 0) for step in solution.get('steps', [])], ensure_ascii=False),
                        solution_verified=False,
                        solution_generated_at=datetime.now()
                    )

                    if success:
                        successful_saves += 1
                        results_summary['details'].append({
                            'question_id': question_id,
                            'status': 'success',
                            'message': 'Solution generated and saved successfully'
                        })
                    else:
                        failed_saves += 1
                        results_summary['details'].append({
                            'question_id': question_id,
                            'status': 'db_error',
                            'message': 'Failed to save solution to database'
                        })

                except Exception as e:
                    failed_saves += 1
                    logger.error(f"Error processing solution for question {question_id}: {e}")
                    results_summary['details'].append({
                        'question_id': question_id,
                        'status': 'processing_error',
                        'message': f"Error processing: {str(e)}"
                    })

            results_summary['successful_solutions'] = successful_saves
            results_summary['failed_solutions'] = solution_errors
            results_summary['database_errors'] = failed_saves

            logger.info(f"Batch solving completed: {successful_saves} successful, {solution_errors} AI errors, {failed_saves} DB errors")

            if successful_saves > 0:
                message = f"Batch solving completed: {successful_saves}/{len(solutions)} questions solved successfully"
                return True, message, results_summary
            else:
                message = f"Batch solving failed: No questions solved successfully ({solution_errors} AI errors, {failed_saves} DB errors)"
                return False, message, results_summary

        except Exception as e:
            logger.error(f"Batch solving error: {e}")
            return False, f"Batch solving error: {str(e)}", {}

    def get_question_solution(self, question_id: int) -> Tuple[bool, str, Optional[Dict]]:
        """
        Get the current solution for a question from database.

        Args:
            question_id: ID of the question

        Returns:
            Tuple of (success, message, solution_data)
        """
        try:
            question = db_manager.get_question_by_id(question_id)
            if not question:
                return False, "Question not found", None

            if not question.solution_answer:
                return False, "No solution available for this question", None

            solution_data = {
                'answer': question.solution_answer,
                'steps': json.loads(question.solution_steps) if question.solution_steps else [],
                'points': json.loads(question.solution_points) if question.solution_points else [],
                'verified': question.solution_verified,
                'generated_at': question.solution_generated_at.isoformat() if question.solution_generated_at else None
            }

            return True, "Solution retrieved successfully", solution_data

        except Exception as e:
            logger.error(f"Error retrieving solution for question {question_id}: {e}")
            return False, f"Error retrieving solution: {str(e)}", None

    def verify_solution(self, question_id: int, verified: bool = True) -> Tuple[bool, str]:
        """
        Mark a question's solution as verified or unverified by teacher.

        Args:
            question_id: ID of the question
            verified: Whether to mark as verified

        Returns:
            Tuple of (success, message)
        """
        try:
            success = db_manager.update_question_solution_verification(question_id, verified)
            if success:
                status = "verified" if verified else "unverified"
                return True, f"Solution marked as {status}"
            else:
                return False, "Failed to update verification status"

        except Exception as e:
            logger.error(f"Error updating verification for question {question_id}: {e}")
            return False, f"Error updating verification: {str(e)}"

# Create singleton instance
question_solver_service = QuestionSolverService()