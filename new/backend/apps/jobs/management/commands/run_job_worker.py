import json
import time
from contextlib import contextmanager
from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.jobs.models import Job
from apps.jobs.realesrgan import upscale_image
from django.conf import settings
from pathlib import Path
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from apps.submissions.models import SubmissionItem
from apps.submissions.grading import grade_item_and_persist


@contextmanager
def locked_job(job_id: int):
    with transaction.atomic():
        job = Job.objects.select_for_update(skip_locked=True).get(id=job_id)
        yield job


def handle_upscale(job: Job):
    payload = job.payload or {}
    image_paths = payload.get("image_paths", [])
    submission_id = payload.get("submission_id")
    out_paths = []
    for p in image_paths:
        out = upscale_image(Path(p), settings.MEDIA_SUBMISSIONS_DIR / f"submission_{submission_id}" / "upscaled")
        out_paths.append(str(out))
    return {"upscaled_paths": out_paths}


HANDLERS = {
    "UPSCALE_SUBMISSION": handle_upscale,
    "GRADE_ITEM": lambda job: (grade_item_and_persist(SubmissionItem.objects.get(id=job.payload.get("submission_item_id"))) or {"graded": True}),
}


class Command(BaseCommand):
    help = "Run simple DB-backed job worker"

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true")

    def handle(self, *args, **options):
        run_once = options.get("once", False)
        while True:
            job = (
                Job.objects
                .filter(status=Job.Status.PENDING)
                .order_by("created_at")
                .first()
            )
            if not job:
                if run_once:
                    return
                time.sleep(1)
                continue

            try:
                with locked_job(job.id):
                    job.refresh_from_db()
                    if job.status != Job.Status.PENDING:
                        continue
                    job.status = Job.Status.RUNNING
                    job.started_at = datetime.utcnow()
                    job.save(update_fields=["status", "started_at"])

                handler = HANDLERS.get(job.type)
                if not handler:
                    raise ValueError(f"Unknown job type: {job.type}")
                result = handler(job)

                job.refresh_from_db()
                job.status = Job.Status.SUCCEEDED
                job.result = result
                job.finished_at = datetime.utcnow()
                job.save(update_fields=["status", "result", "finished_at"])
                # Emit websocket notification
                try:
                    channel_layer = get_channel_layer()
                    async_to_sync(channel_layer.group_send)(
                        "notifications",
                        {"type": "notify", "payload": {"event": job.type, "job_id": job.id, "status": job.status, "result": job.result}},
                    )
                except Exception:
                    pass
            except Exception as e:
                job.refresh_from_db()
                job.status = Job.Status.FAILED
                job.error = str(e)
                job.retries += 1
                job.finished_at = datetime.utcnow()
                job.save(update_fields=["status", "error", "retries", "finished_at"])
            finally:
                if run_once:
                    return
                time.sleep(0.1)


