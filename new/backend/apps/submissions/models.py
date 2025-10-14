from django.db import models
from apps.exams.models import Exam, Question


class Submission(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="submissions")
    student_name = models.CharField(max_length=255)
    original_image_paths = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"{self.student_name} - exam {self.exam_id}"


class SubmissionItem(models.Model):
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="items")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="submission_items")

    source_page_indices = models.JSONField(null=True, blank=True)
    answer_image_paths = models.JSONField(null=True, blank=True)
    has_multiple_images = models.BooleanField(default=False)

    answer_bbox = models.JSONField(null=True, blank=True)
    original_image_dimensions = models.JSONField(null=True, blank=True)
    annotations = models.JSONField(null=True, blank=True)

    def __str__(self) -> str:
        return f"Item {self.id} for sub {self.submission_id} / q {self.question_id}"


class Grading(models.Model):
    submission_item = models.OneToOneField(SubmissionItem, on_delete=models.CASCADE, related_name="grading")
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name="gradings")

    is_correct = models.BooleanField()
    error_description = models.TextField(null=True, blank=True)
    error_phrases = models.JSONField(null=True, blank=True)
    critical_errors = models.JSONField(null=True, blank=True)
    part_errors = models.JSONField(null=True, blank=True)
    partial_credit = models.BooleanField(default=False)

    teacher_notes = models.TextField(null=True, blank=True)
    clarify_notes = models.TextField(null=True, blank=True)
    graded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Grading for item {self.submission_item_id}"


