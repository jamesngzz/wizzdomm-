# Pages module for Teacher Assistant v2.0
# Internal imports - not exposed as separate routes
from .create_exam_page import show_create_exam_page as _create_exam
from .digitize_exam_page import show_digitize_exam_page as _digitize_exam  
from .submissions_page import show_submissions_page as _submissions
from .grading_page import show_grading_page as _grading
from .results_page import show_results_page as _results

# Export with original names for internal use only
show_create_exam_page = _create_exam
show_digitize_exam_page = _digitize_exam
show_submissions_page = _submissions
show_grading_page = _grading
show_results_page = _results

__all__ = [
    'show_create_exam_page',
    'show_digitize_exam_page', 
    'show_submissions_page',
    'show_grading_page',
    'show_results_page'
]