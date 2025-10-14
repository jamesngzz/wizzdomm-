# Deployment Notes (3–4 concurrent users)

## What to keep running
- Web server (ASGI): `uvicorn config.asgi:application --host 0.0.0.0 --port 8080 --timeout-keep-alive 60`
- 3 workers for grading jobs (via Supervisor)
  - Config files already in repo:
    - `supervisord.conf` (user-scoped)
    - `supervisor.d/ta-worker.conf` (numprocs=3)

## Start Supervisor (user-scoped; no sudo)
```bash
cd /Users/admin/học/teacher-assistant-v2/new/backend
/opt/homebrew/opt/supervisor/bin/supervisord -c supervisord.conf
/opt/homebrew/opt/supervisor/bin/supervisorctl -c supervisord.conf reread
/opt/homebrew/opt/supervisor/bin/supervisorctl -c supervisord.conf update
/opt/homebrew/opt/supervisor/bin/supervisorctl -c supervisord.conf status
```
Expect 3 RUNNING processes.

## Environment
- Required: `GEMINI_API_KEY`
- Optional:
  - `MAX_CONCURRENT_GRADING` (default 10 per submission enqueue; workers process queue sequentially)
  - `TIME_ZONE=Asia/Ho_Chi_Minh`

## Verifications
```bash
# Job counts
. .venv/bin/activate
python manage.py shell -c "from apps.jobs.models import Job as J;import json;s=lambda st:J.objects.filter(status=st).count();print(json.dumps({'pending':s('pending'),'running':s('running'),'succeeded':s('succeeded'),'failed':s('failed')},ensure_ascii=False))"

# Grading activity
tail -f grading.log

# Worker logs
tail -f worker_out.log worker_err.log
```

## Operational notes
- Concurrency: driven by number of workers. For ~15–20s/10 items: 5 workers; for 3–4 users, 3 workers is acceptable (~30–40s per 10 items).
- Cost: parallelism does not increase token usage; same total cost.
- Database: SQLite OK for dev/small teams; consider PostgreSQL for heavier concurrency.
- Channels: using in-memory layer; if you need cross-process WebSocket reliability, switch to Redis.

## Troubleshooting
- Jobs stuck at pending → no worker running or missing `GEMINI_API_KEY`.
- 429 from Gemini → reduce concurrency or upgrade plan.
- Naive datetime warnings → harmless; can switch to `timezone.now()` in worker for strict TZ.
