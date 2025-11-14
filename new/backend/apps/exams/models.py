"""
FIXED DATA MODEL V2 - exams/models.py
All fixes applied:
1. Added unique_together constraint on Question(exam, order_index, part_label)
2. Added updated_at timestamps
3. Added indexes for performance
4. Added validation for order_index
"""

from django.db import models
from django.core.exceptions import ValidationError


class Exam(models.Model):
    name = models.CharField(max_length=255)
    topic = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=16)
    original_image_paths = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    class Meta:
        indexes = [
            models.Index(fields=["-created_at"]),  # For recent exams
        ]

    def clean(self):
        """Validate original_image_paths is a list."""
        if self.original_image_paths is not None:
            if not isinstance(self.original_image_paths, list):
                raise ValidationError("original_image_paths must be a list")
            for path in self.original_image_paths:
                if not isinstance(path, str):
                    raise ValidationError("original_image_paths must contain strings")

    def __str__(self) -> str:
        return self.name


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")

    question_image_paths = models.JSONField(null=True, blank=True)
    has_multiple_images = models.BooleanField(default=False)  # TODO: Consider removing, derive from question_image_paths

    order_index = models.IntegerField()
    part_label = models.CharField(max_length=32, null=True, blank=True)

    solution_answer = models.TextField(null=True, blank=True)
    solution_steps = models.JSONField(null=True, blank=True)
    solution_points = models.JSONField(null=True, blank=True)
    solution_verified = models.BooleanField(default=False)
    solution_generated_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)  # FIX: Added
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    class Meta:
        # FIX: Prevent duplicate question numbers in same exam
        unique_together = [("exam", "order_index", "part_label")]
        indexes = [
            models.Index(fields=["exam", "order_index"]),  # For ordering questions
            models.Index(fields=["exam"]),                 # For listing all questions
        ]

    def clean(self):
        """Validate order_index and JSON fields."""
        if self.order_index < 1:
            raise ValidationError("order_index must be >= 1")
        
        if self.question_image_paths is not None:
            if not isinstance(self.question_image_paths, list):
                raise ValidationError("question_image_paths must be a list")
            for path in self.question_image_paths:
                if not isinstance(path, str):
                    raise ValidationError("question_image_paths must contain strings")
        
        # Validate has_multiple_images consistency
        expected_multiple = len(self.question_image_paths or []) > 1
        if self.has_multiple_images != expected_multiple:
            raise ValidationError(
                f"has_multiple_images ({self.has_multiple_images}) inconsistent with "
                f"question_image_paths length ({len(self.question_image_paths or [])})"
            )

    def __str__(self) -> str:
        label = f"{self.order_index}{self.part_label or ''}"
        return f"Question {label} of {self.exam_id}"
