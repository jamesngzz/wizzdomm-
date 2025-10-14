from rest_framework import serializers
from apps.exams.models import Exam
from .models import Submission


class SubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Submission
        fields = [
            "id",
            "exam",
            "student_name",
            "original_image_paths",
            "created_at",
        ]
        read_only_fields = ["id", "original_image_paths", "created_at"]



