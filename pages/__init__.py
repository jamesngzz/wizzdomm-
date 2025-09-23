# Pages module for Teacher Assistant v2.0
# Internal imports - not exposed as separate routes
from .create_exam_page import show_create_exam_page as _create_exam
from .digitize_exam_page import show_digitize_exam_page as _digitize_exam
from .submissions_page import show_submissions_page as _submissions
from .grading_results_page import show_grading_results_page as _grading_results

# Export with original names for internal use only
show_create_exam_page = _create_exam
show_digitize_exam_page = _digitize_exam
show_submissions_page = _submissions
show_grading_results_page = _grading_results

__all__ = [
    'show_create_exam_page',
    'show_digitize_exam_page',
    'show_submissions_page',
    'show_grading_results_page'
]