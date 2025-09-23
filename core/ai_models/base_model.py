from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseGradingModel(ABC):
    """
    Abstract Base Class for AI grading models.
    Defines the interface that all grading models must implement.
    """
    
    @abstractmethod
    def grade_image_pair(self, question_image_paths: List[str], answer_image_paths: List[str],
                        clarify: str = None, previous_grading: Dict[str, Any] = None, solution: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Grades a pair of question and answer images.

        Args:
            question_image_paths: A list of file paths to the question images.
            answer_image_paths: A list of file paths to the student's answer images.
            clarify: Optional teacher clarification for re-grading (e.g., "Ở bước cuối là y^6, không phải y^8")
            previous_grading: Optional previous grading result for context when re-grading
            solution: Optional solution reference with description and content only

        Returns:
            A dictionary containing the grading result, conforming to a standardized format.
            e.g., {"is_correct": bool, "critical_errors": list, "part_errors": list, "partial_credit": bool}
        """
        pass

    def grade_batch(self, items: List[Dict]) -> List[Dict[str, Any]]:
        """
        Grades a batch of items. The default implementation iterates and calls
        grade_image_pair, but subclasses can override this for more efficient batching.
        
        Args:
            items: A list of dictionaries, where each dict contains 'question_image_paths'
                   and 'answer_image_paths'.
                   
        Returns:
            A list of grading result dictionaries.
        """
        import logging
        import os
        logger = logging.getLogger(__name__)
        
        logger.info(f"Starting batch grading for {len(items)} items")
        results = []
        for i, item in enumerate(items, 1):
            logger.info(f"Batch item {i}/{len(items)}:")
            logger.info(f"  Question images: {[os.path.basename(p) for p in item['question_image_paths']]}")
            logger.info(f"  Answer images: {[os.path.basename(p) for p in item['answer_image_paths']]}")
            
            result = self.grade_image_pair(
                question_image_paths=item['question_image_paths'],
                answer_image_paths=item['answer_image_paths'],
                clarify=item.get('clarify'),
                previous_grading=item.get('previous_grading'),
                solution=item.get('solution')
            )
            results.append(result)
        
        logger.info(f"Batch grading completed for {len(items)} items")
        return results