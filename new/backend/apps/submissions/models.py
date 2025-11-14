"""
FIXED DATA MODEL V2 - submissions/models.py
All critical fixes applied:
1. Added unique_together constraint on SubmissionItem(submission, question)
2. Added exam consistency validation
3. Added updated_at timestamps
4. Added indexes for performance
5. Added JSON field validation
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q, F
from apps.exams.models import Exam, Question


class Submission(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="submissions")
    student_name = models.CharField(max_length=255)
    original_image_paths = models.JSONField(null=True, blank=True)
    
    # Triage results and flags
    triage_report = models.JSONField(null=True, blank=True)
    triage_decision = models.CharField(max_length=32, null=True, blank=True)
    triage_readability_score = models.FloatField(null=True, blank=True)
    triage_confidence = models.FloatField(null=True, blank=True)
    flagged_for_human = models.BooleanField(default=False)

    # Enhanced tier classification
    triage_tier = models.IntegerField(
        null=True, blank=True,
        choices=[(1, 'Tier 1'), (2, 'Tier 2'), (3, 'Tier 3')]
    )
    triage_score = models.FloatField(null=True, blank=True)  # 1.0-5.0
    triage_label = models.CharField(max_length=32, null=True, blank=True)
    # Values: "good", "moderate", "poor", "very poor", "unreadable"

    recommended_solution = models.CharField(max_length=128, null=True, blank=True)
    # Values: "General VLM (Gemini Flash)", "Flash + Warning System",
    #         "Deep Analysis Required (Gemini Pro + Human Review)"
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    class Meta:
        indexes = [
            models.Index(fields=["exam", "created_at"]),  # For listing submissions by exam
            models.Index(fields=["flagged_for_human"]),   # For review queue
        ]

    def clean(self):
        """Validate triage_score range if provided."""
        if self.triage_score is not None:
            if not (1.0 <= self.triage_score <= 5.0):
                raise ValidationError("triage_score must be between 1.0 and 5.0")
        
        # Validate original_image_paths is a list
        if self.original_image_paths is not None:
            if not isinstance(self.original_image_paths, list):
                raise ValidationError("original_image_paths must be a list")
            for path in self.original_image_paths:
                if not isinstance(path, str):
                    raise ValidationError("original_image_paths must contain strings")

    def __str__(self) -> str:
        return f"{self.student_name} - exam {self.exam_id}"


class SubmissionItem(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="submission_items")

    source_page_indices = models.JSONField(null=True, blank=True)
    answer_image_paths = models.JSONField(null=True, blank=True)
    has_multiple_images = models.BooleanField(default=False)  # TODO: Consider removing, derive from answer_image_paths

    answer_bbox = models.JSONField(null=True, blank=True)
    original_image_dimensions = models.JSONField(null=True, blank=True)
    annotations = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)  # FIX: Added
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    class Meta:
        # FIX: CRITICAL - Prevent duplicate items for same question
        unique_together = [("submission", "question")]
        indexes = [
            # FIX: Performance - Common query patterns
            models.Index(fields=["submission", "question"]),  # For unique lookup
            models.Index(fields=["submission"]),              # For listing all items
            models.Index(fields=["question"]),                # For question analytics
        ]
        # FIX: Database-level constraint for exam consistency
        # Note: SQLite doesn't support CheckConstraint with F() expressions on related fields
        # Python validation in clean() will catch it on all databases
        # For PostgreSQL, we could add this constraint manually in a migration if needed
        # constraints = [
        #     models.CheckConstraint(
        #         check=Q(submission__exam_id=F('question__exam_id')),
        #         name='submission_item_exam_consistency'
        #     )
        # ]

    def clean(self):
        """Validate data integrity and JSON fields."""
        # FIX: CRITICAL - Ensure exam consistency
        if self.submission_id and self.question_id:
            if self.submission.exam_id != self.question.exam_id:
                raise ValidationError(
                    f"Submission (exam_id={self.submission.exam_id}) and "
                    f"Question (exam_id={self.question.exam_id}) must belong to the same exam"
                )
        
        # Validate JSON fields
        if self.source_page_indices is not None:
            if not isinstance(self.source_page_indices, list):
                raise ValidationError("source_page_indices must be a list")
            for idx in self.source_page_indices:
                if not isinstance(idx, int):
                    raise ValidationError("source_page_indices must contain integers")
        
        if self.answer_image_paths is not None:
            if not isinstance(self.answer_image_paths, list):
                raise ValidationError("answer_image_paths must be a list")
            for path in self.answer_image_paths:
                if not isinstance(path, str):
                    raise ValidationError("answer_image_paths must contain strings")
        
        # Validate has_multiple_images consistency
        expected_multiple = len(self.answer_image_paths or []) > 1
        if self.has_multiple_images != expected_multiple:
            raise ValidationError(
                f"has_multiple_images ({self.has_multiple_images}) inconsistent with "
                f"answer_image_paths length ({len(self.answer_image_paths or [])})"
            )
        
        # Validate answer_bbox structure if provided
        if self.answer_bbox is not None:
            if not isinstance(self.answer_bbox, dict):
                raise ValidationError("answer_bbox must be a dictionary")
            required_keys = ['x', 'y', 'w', 'h']
            for key in required_keys:
                if key not in self.answer_bbox:
                    raise ValidationError(f"answer_bbox must contain '{key}' key")

    def __str__(self) -> str:
        return f"Item {self.id} for sub {self.submission_id} / q {self.question_id}"


# Legacy Grading model removed - now using GradingResult from apps.grading
