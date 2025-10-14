from django.db import models


class Exam(models.Model):
    name = models.CharField(max_length=255)
    topic = models.CharField(max_length=100)
    grade_level = models.CharField(max_length=16)
    original_image_paths = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class Question(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name="questions")

    question_image_paths = models.JSONField(null=True, blank=True)
    has_multiple_images = models.BooleanField(default=False)

    order_index = models.IntegerField()
    part_label = models.CharField(max_length=32, null=True, blank=True)

    solution_answer = models.TextField(null=True, blank=True)
    solution_steps = models.JSONField(null=True, blank=True)
    solution_points = models.JSONField(null=True, blank=True)
    solution_verified = models.BooleanField(default=False)
    solution_generated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        label = f"{self.order_index}{self.part_label or ''}"
        return f"Question {label} of {self.exam_id}"


