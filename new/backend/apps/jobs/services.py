from typing import Optional, List, Dict, Any
from apps.jobs.models import Job


def enqueue(job_type: str, payload: Optional[dict] = None, max_retries: int = 3) -> int:
	job = Job.objects.create(type=job_type, payload=payload or {}, max_retries=max_retries)
	return job.id


def enqueue_upscale_submission(submission_id: int, image_paths: List[str]) -> int:
	return enqueue("UPSCALE_SUBMISSION", {"submission_id": submission_id, "image_paths": image_paths})


def _find_active_job(job_type: str, payload_filters: Dict[str, Any]) -> Optional[Job]:
    qs = Job.objects.filter(type=job_type, status__in=[Job.Status.PENDING, Job.Status.RUNNING])
    for key, value in payload_filters.items():
        qs = qs.filter(**{f"payload__{key}": value})
    return qs.first()


def enqueue_grade_item_if_not_exists(submission_item_id: int) -> Optional[int]:
    """Return existing job id if a pending/running one exists, else enqueue a new one.
    Returns job id, or None if cannot enqueue.
    """
    existing = _find_active_job("GRADE_ITEM", {"submission_item_id": submission_item_id})
    if existing:
        return existing.id
    return enqueue("GRADE_ITEM", {"submission_item_id": submission_item_id})

