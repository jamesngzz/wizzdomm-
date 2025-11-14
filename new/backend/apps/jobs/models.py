"""
FIXED DATA MODEL V2 - jobs/models.py
All fixes applied:
1. Added indexes for worker queries (type, status)
2. Added validation for retries
3. Added updated_at to GradingBatch
"""

from django.db import models
from django.core.exceptions import ValidationError


class GradingBatch(models.Model):
    """Tracks batch grading operations for progress monitoring."""
    batch_id = models.CharField(max_length=64, unique=True, db_index=True)
    total_items = models.IntegerField()
    completed_items = models.IntegerField(default=0)
    failed_items = models.IntegerField(default=0)

    class Status(models.TextChoices):
        PENDING = "pending"
        PROCESSING = "processing"
        COMPLETED = "completed"
        FAILED = "failed"

    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING
    )
    submission_ids = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["status", "-created_at"]),  # For monitoring
        ]

    def clean(self):
        """Validate batch counts."""
        if self.completed_items < 0 or self.failed_items < 0:
            raise ValidationError("Counts cannot be negative")
        if self.completed_items + self.failed_items > self.total_items:
            raise ValidationError("Completed + failed cannot exceed total")

    def __str__(self) -> str:
        return f"Batch[{self.batch_id}] {self.status} - {self.completed_items}/{self.total_items}"


class Job(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending"
        RUNNING = "running"
        SUCCEEDED = "succeeded"
        FAILED = "failed"
        CANCELED = "canceled"

    type = models.CharField(max_length=64)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    payload = models.JSONField(null=True, blank=True)
    result = models.JSONField(null=True, blank=True)
    error = models.TextField(null=True, blank=True)
    retries = models.IntegerField(default=0)
    max_retries = models.IntegerField(default=3)
    scheduled_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    parent_job = models.ForeignKey("self", null=True, blank=True, on_delete=models.SET_NULL, related_name="children")
    owner = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # FIX: CRITICAL - Indexes for worker queries
        indexes = [
            models.Index(fields=["type", "status"]),      # For worker queries (most common)
            models.Index(fields=["status", "created_at"]), # For job monitoring
            models.Index(fields=["-created_at"]),        # For recent jobs
            models.Index(fields=["parent_job"]),          # For child job queries
        ]
        # FIX: Database-level validation
        constraints = [
            models.CheckConstraint(
                check=models.Q(retries__lte=models.F('max_retries')),
                name='job_retries_valid'
            )
        ]

    def clean(self):
        """Validate retries and status."""
        if self.retries < 0:
            raise ValidationError("retries cannot be negative")
        if self.retries > self.max_retries:
            raise ValidationError("retries cannot exceed max_retries")

    def __str__(self) -> str:
        return f"Job[{self.id}] {self.type} - {self.status}"
