"""
FIXED DATA MODEL V2 - grading/models.py
All critical fixes applied:
1. Added bbox validation to OcrLine
2. Added score validation to GradingResult
3. Fixed GradingResult.question_id (use ForeignKey)
4. Added choice fields for status and refined_by
5. Added updated_at timestamps
6. Added missing indexes
7. Increased image_path max_length
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.db.models import Q, F
from apps.submissions.models import Submission, SubmissionItem
from apps.exams.models import Question


class OcrPage(models.Model):
    """OCR metadata for a single page of a submission."""
    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="ocr_pages")
    page_index = models.IntegerField()
    # FIX: Increased max_length for S3 keys
    image_path = models.CharField(max_length=1024)  # S3 key limit is 1024 chars
    width = models.IntegerField()
    height = models.IntegerField()
    sha256 = models.CharField(max_length=64, db_index=True)  # for caching
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    # Page-level refinement metadata
    page_summary = models.TextField(null=True, blank=True)
    overall_confidence = models.FloatField(null=True, blank=True)
    page_level_issues = models.JSONField(null=True, blank=True)
    critical_ambiguities = models.JSONField(null=True, blank=True)

    # Auto-rotation metadata
    auto_rotate_confidence = models.FloatField(null=True, blank=True, help_text="Confidence level of auto-rotation detection (0-1)")
    auto_rotate_degrees = models.IntegerField(null=True, blank=True, help_text="Degrees of rotation applied by Mathpix (0, 90, 180, 270)")
    manual_rotation_applied = models.BooleanField(default=False, help_text="Whether manual rotation was applied due to low auto-rotation confidence")
    manual_rotation_degrees = models.IntegerField(null=True, blank=True, help_text="Degrees of manual rotation applied when auto-rotation confidence was low")

    class Meta:
        unique_together = [("submission", "page_index")]
        indexes = [
            models.Index(fields=["submission", "page_index"]),
            models.Index(fields=["sha256"]),
        ]

    def clean(self):
        """Validate page_index is non-negative."""
        if self.page_index < 0:
            raise ValidationError("page_index must be non-negative")

    def __str__(self):
        return f"OCR page {self.page_index} for submission {self.submission_id}"


class RefinementSource(models.TextChoices):
    """Source of OCR refinement."""
    FLASH = "flash", "Gemini Flash"
    PRO = "pro", "Gemini Pro"


class OcrLine(models.Model):
    """A single line extracted from OCR with bounding box."""
    page = models.ForeignKey(OcrPage, on_delete=models.CASCADE, related_name="lines")
    line_index = models.IntegerField()  # within the page
    x1 = models.IntegerField()
    y1 = models.IntegerField()
    x2 = models.IntegerField()
    y2 = models.IntegerField()
    polygon = models.JSONField(null=True, blank=True)  # original Mathpix cnt format
    
    # Mathpix OCR (original)
    text = models.TextField(blank=True)
    latex = models.TextField(blank=True)
    confidence = models.FloatField(default=0.0)

    # Refined OCR fields (Gemini Flash)
    gemini_text = models.TextField(null=True, blank=True)
    gemini_latex = models.TextField(null=True, blank=True)
    gemini_confidence = models.FloatField(null=True, blank=True)

    # Refined OCR fields (Gemini Pro)
    gemini_pro_text = models.TextField(null=True, blank=True)
    gemini_pro_latex = models.TextField(null=True, blank=True)
    gemini_pro_confidence = models.FloatField(null=True, blank=True)
    gemini_pro_ambiguities = models.JSONField(null=True, blank=True)

    # Refinement metadata
    # FIX: Use choice field instead of free text
    refined_by = models.CharField(
        max_length=16,
        choices=RefinementSource.choices,
        null=True,
        blank=True
    )
    changed_from_mathpix = models.BooleanField(default=False)
    change_reason = models.TextField(null=True, blank=True)

    # Handwriting quality flags detected during refinement
    handwriting_flag = models.BooleanField(default=False)
    handwriting_notes = models.JSONField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)  # FIX: Added
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    class Meta:
        unique_together = [("page", "line_index")]
        indexes = [
            models.Index(fields=["page", "line_index"]),
        ]
        # FIX: CRITICAL - Database-level bbox validation
        # Note: SQLite supports simple CheckConstraint, but Python validation in clean() is primary
        constraints = [
            models.CheckConstraint(
                check=Q(x2__gt=F('x1'), y2__gt=F('y1'), x1__gte=0, y1__gte=0),
                name='ocr_line_valid_bbox'
            )
        ]

    def clean(self):
        """FIX: CRITICAL - Validate bounding box coordinates."""
        if self.x2 <= self.x1:
            raise ValidationError("x2 must be greater than x1")
        if self.y2 <= self.y1:
            raise ValidationError("y2 must be greater than y1")
        if self.x1 < 0 or self.y1 < 0:
            raise ValidationError("Coordinates must be non-negative")
        if self.line_index < 0:
            raise ValidationError("line_index must be non-negative")

    def __str__(self):
        return f"Line {self.line_index} on page {self.page.page_index}"

    @property
    def line_id(self):
        """Generate standardized lineId: p{page_index}-l{line_index}"""
        return f"p{self.page.page_index}-l{self.line_index}"

    @property
    def bbox(self):
        """Return bbox as [x1, y1, x2, y2] for API."""
        return [self.x1, self.y1, self.x2, self.y2]
    
    @property
    def active_text(self):
        """FIX: Source of truth for OCR text (priority: Pro > Flash > Mathpix)."""
        return self.gemini_pro_text or self.gemini_text or self.text or ""
    
    @property
    def active_latex(self):
        """Source of truth for OCR LaTeX."""
        return self.gemini_pro_latex or self.gemini_latex or self.latex or ""


class GradingResult(models.Model):
    """Step-by-step grading result for a submission item."""
    submission_item = models.OneToOneField(
        SubmissionItem, on_delete=models.CASCADE, related_name="step_grading_result"
    )
    # FIX: CRITICAL - Use ForeignKey instead of denormalized IntegerField
    question = models.ForeignKey(
        Question,
        on_delete=models.CASCADE,
        related_name="grading_results",
        db_index=True
    )
    is_correct = models.BooleanField(default=False)
    score = models.FloatField(default=0.0)
    max_score = models.FloatField(default=0.0)
    summary_short = models.CharField(max_length=160, blank=True)
    raw_llm = models.TextField(blank=True)  # JSON string for audit
    model_name = models.CharField(max_length=64, default="gemini-2.5-flash")
    prompt_version = models.CharField(max_length=32, default="v1")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    # Aggregated handwriting summary and review flags
    handwriting_summary = models.JSONField(null=True, blank=True)
    needs_human_review = models.BooleanField(default=False)
    llm_confidence_score = models.FloatField(null=True, blank=True)

    # Phase 2/3 metadata
    phase2_mode = models.BooleanField(default=False, help_text="Whether this result used Phase 2 full-page OCR")
    phase3_mode = models.BooleanField(default=False, help_text="Whether this result used Phase 3 parallel grading")
    full_pages_processed = models.IntegerField(null=True, blank=True, help_text="Number of full pages processed")
    question_lines_extracted = models.IntegerField(null=True, blank=True, help_text="Number of OCR lines extracted for this question")

    # Error details for debugging
    critical_errors = models.JSONField(null=True, blank=True, help_text="Critical errors that prevented grading")
    part_errors = models.JSONField(null=True, blank=True, help_text="Partial errors found during grading")
    partial_credit = models.BooleanField(default=False, help_text="Whether partial credit was awarded")

    class Meta:
        indexes = [
            models.Index(fields=["submission_item"]),
            models.Index(fields=["question"]),  # FIX: Changed from question_id
            # FIX: Performance - Common query patterns
            models.Index(fields=["needs_human_review"]),  # For review queue
            models.Index(fields=["is_correct"]),          # For statistics
            models.Index(fields=["-created_at"]),         # For recent results
            models.Index(fields=["question", "is_correct"]),  # For question analytics
        ]
        # FIX: CRITICAL - Database-level score validation
        # Note: SQLite doesn't support CheckConstraint with F() expressions on related fields
        # Python validation in clean() will catch these issues on all databases
        constraints = [
            models.CheckConstraint(
                check=Q(score__gte=0, max_score__gte=0, score__lte=F('max_score')),
                name='grading_result_valid_scores'
            ),
            # Note: question consistency check removed - SQLite doesn't support F() on related fields
            # Python validation in clean() will catch this
        ]

    def clean(self):
        """FIX: CRITICAL - Validate scores."""
        if self.score < 0 or self.max_score < 0:
            raise ValidationError("Scores must be non-negative")
        if self.score > self.max_score:
            raise ValidationError("Score cannot exceed max_score")
        if self.max_score == 0 and self.score > 0:
            raise ValidationError("Cannot have score when max_score is 0")
        
        # Ensure question matches submission_item.question
        if self.submission_item_id and self.question_id:
            if self.submission_item.question_id != self.question.id:
                raise ValidationError(
                    f"question.id ({self.question.id}) must match "
                    f"submission_item.question_id ({self.submission_item.question_id})"
                )

    def __str__(self):
        return f"GradingResult for item {self.submission_item_id}"
    
    @property
    def question_id(self):
        """Backward compatibility property for question_id."""
        return self.question.id if hasattr(self, 'question') and self.question else None


class GradingStepStatus(models.TextChoices):
    """Status of a grading step."""
    CORRECT = "correct", "Correct"
    INCORRECT = "incorrect", "Incorrect"
    MISSING = "missing", "Missing"
    NOT_APPLICABLE = "na", "Not Applicable"
    PARTIALLY_CORRECT = "partially_correct", "Partially Correct"


class GradingStep(models.Model):
    """A single step in step-by-step grading."""
    result = models.ForeignKey(GradingResult, on_delete=models.CASCADE, related_name="steps")
    step_id = models.CharField(max_length=64)
    step_index = models.IntegerField()
    label = models.CharField(max_length=128)
    # FIX: Use choice field instead of free text
    status = models.CharField(max_length=32, choices=GradingStepStatus.choices)
    weight = models.FloatField(default=1.0)
    reason = models.TextField(blank=True)
    annotation = models.JSONField(default=dict)  # {wrong_snippet, correct_snippet, note_short}
    
    created_at = models.DateTimeField(auto_now_add=True)  # FIX: Added
    updated_at = models.DateTimeField(auto_now=True)  # FIX: Added

    class Meta:
        unique_together = [("result", "step_index")]
        ordering = ["step_index"]
        indexes = [
            models.Index(fields=["result", "step_index"]),  # For ordering
            models.Index(fields=["status"]),  # For filtering by status
        ]

    def clean(self):
        """Validate weight is positive."""
        if self.weight <= 0:
            raise ValidationError("weight must be positive")
        if self.step_index < 0:
            raise ValidationError("step_index must be non-negative")

    def __str__(self):
        return f"Step {self.step_index}: {self.label} ({self.status})"


class StepLineMap(models.Model):
    """Mapping between grading steps and OCR lines."""
    step = models.ForeignKey(GradingStep, on_delete=models.CASCADE, related_name="line_maps")
    line = models.ForeignKey(OcrLine, on_delete=models.CASCADE, related_name="step_maps")

    class Meta:
        unique_together = [("step", "line")]
        indexes = [
            models.Index(fields=["step"]),
            models.Index(fields=["line"]),
        ]

    def clean(self):
        """FIX: Validate that line and step belong to same submission."""
        if self.step_id and self.line_id:
            step_submission = self.step.result.submission_item.submission_id
            line_submission = self.line.page.submission_id
            if step_submission != line_submission:
                raise ValidationError(
                    f"Step (submission_id={step_submission}) and "
                    f"Line (submission_id={line_submission}) must belong to the same submission"
                )

    def __str__(self):
        return f"Step {self.step.step_id} -> Line {self.line.line_id}"
