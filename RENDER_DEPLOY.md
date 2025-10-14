# Render Deployment Guide

## Services
- ta-backend (Web Service, Docker, Starter)
- ta-worker (Background Worker, Docker, Starter)
- ta-frontend (Static Site)
- ta-postgres (Managed Postgres, Starter)
- ta-redis (Managed Redis, Starter)

## Backend env (Web + Worker)
- SECRET_KEY: strong random string
- DEBUG=false
- ALLOWED_HOSTS=yourapp.onrender.com
- TIME_ZONE=UTC
- DB_ENGINE=django.db.backends.postgresql
- DB_NAME/DB_USER/DB_PASSWORD/DB_HOST/DB_PORT: from Render Postgres
- CHANNEL_REDIS_URL: from Render Redis (connection string)
- CORS_ALLOWED_ORIGINS=https://your-frontend.onrender.com
- CSRF_TRUSTED_ORIGINS=https://your-frontend.onrender.com
- MAX_CONCURRENT_GRADING=10
- AUTO_GRADE_ON_CREATE=false
- OPENAI_API_KEY, GEMINI_API_KEY (optional)

## Frontend env (Static Site)
- VITE_API_URL=https://yourapp.onrender.com/api
- VITE_WS_URL=wss://yourapp.onrender.com/ws/notifications/

## Build & Deploy
1. Create `ta-postgres`, `ta-redis` in Render.
2. Create `ta-backend` Web Service (Docker, root `new/backend`). Attach env, mount a 20GB Persistent Disk at `/app/media`.
3. Create `ta-worker` Background Worker with same env and disk; command: `python manage.py run_job_worker`.
4. Create `ta-frontend` Static Site (root `FE`), build `npm ci && npm run build`, publish `dist`.
5. In `ta-backend` shell: `python manage.py migrate` (first time) and optionally `createsuperuser`.

## Notes
- Channels uses Redis automatically when `CHANNEL_REDIS_URL` is set (fallback to in-memory otherwise).
- Media files are stored on the Persistent Disk at `/app/media`.
- Keep secrets in Render env variables, not in git.
- Increase plans when sustained CPU >70% or response p95 > 1s.
