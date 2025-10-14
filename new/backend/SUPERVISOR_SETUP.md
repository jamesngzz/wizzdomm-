# Supervisor setup for 3 workers

This runs 3 persistent Django job workers (`manage.py run_job_worker`).

## 1) Install Supervisor (macOS)
```bash
brew install supervisor
```

## 2) Create program config
Create file: `/usr/local/etc/supervisor.d/ta-worker.conf`

```ini
[program:ta-worker]
command=/bin/zsh -lc 'cd /Users/admin/học/teacher-assistant-v2/new/backend && . .venv/bin/activate && python manage.py run_job_worker'
directory=/Users/admin/học/teacher-assistant-v2/new/backend
numprocs=3
process_name=%(program_name)s_%(process_num)02d
autostart=true
autorestart=true
stderr_logfile=/Users/admin/học/teacher-assistant-v2/new/backend/worker_err.log
stdout_logfile=/Users/admin/học/teacher-assistant-v2/new/backend/worker_out.log
environment=DJANGO_SETTINGS_MODULE="config.settings"
stopasgroup=true
killasgroup=true
```

Note: if Homebrew uses `/opt/homebrew/etc/supervisor.d/`, place it there instead.

## 3) Start Supervisor (first time)
```bash
sudo supervisord -c /usr/local/etc/supervisord.ini || sudo supervisord -c /opt/homebrew/etc/supervisord.ini
```

## 4) Reload programs and verify
```bash
supervisorctl reread && supervisorctl update
supervisorctl status
```
Expect:
```
ta-worker:ta-worker_00                RUNNING
ta-worker:ta-worker_01                RUNNING
ta-worker:ta-worker_02                RUNNING
```

## 5) Logs
```bash
 tail -f /Users/admin/học/teacher-assistant-v2/new/backend/worker_out.log
 tail -f /Users/admin/học/teacher-assistant-v2/new/backend/worker_err.log
```

## 6) Troubleshooting
- Ensure the venv exists at `/Users/admin/học/teacher-assistant-v2/new/backend/.venv` and has dependencies installed.
- If using different shell or path, edit `command` accordingly.
- To stop:
```bash
supervisorctl stop ta-worker:
```

