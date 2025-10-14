from rest_framework import serializers
from .models import Exam, Question
from apps.common.labels import parse_question_label, format_question_label


class ExamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exam
        fields = [
            "id",
            "name",
            "topic",
            "grade_level",
            "original_image_paths",
            "created_at",
        ]
        read_only_fields = ["id", "original_image_paths", "created_at"]


class QuestionSerializer(serializers.ModelSerializer):
    label = serializers.CharField(write_only=True, help_text="e.g., '1a'")
    page_index = serializers.IntegerField(write_only=True, min_value=0)
    bbox = serializers.DictField(write_only=True)

    class Meta:
        model = Question
        fields = [
            "id",
            "exam",
            "order_index",
            "part_label",
            "question_image_paths",
            "has_multiple_images",
            "solution_answer",
            "solution_steps",
            "solution_points",
            "solution_verified",
            "solution_generated_at",
            # write-only inputs
            "label",
            "page_index",
            "bbox",
        ]
        read_only_fields = [
            "id",
            "order_index",
            "part_label",
            "question_image_paths",
            "has_multiple_images",
            "solution_answer",
            "solution_steps",
            "solution_points",
            "solution_verified",
            "solution_generated_at",
        ]



