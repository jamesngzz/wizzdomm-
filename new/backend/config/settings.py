import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")


SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-me")
DEBUG = os.getenv("DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "*").split(",")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Third-party
    "rest_framework",
    "channels",
    "corsheaders",
    # Local apps
    "apps.exams",
    "apps.submissions",
    "apps.jobs",
]


MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]


WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


_database_url = os.getenv("DATABASE_URL")
if _database_url:
    # Prefer DATABASE_URL (e.g., Supabase). Enforce SSL and reuse connections.
    DATABASES = {
        "default": dj_database_url.parse(_database_url, conn_max_age=600, ssl_require=True)
    }
    # With managed poolers (e.g., Supabase PgBouncer), persistent connections can exhaust pool.
    # Default to short-lived connections; override via CONN_MAX_AGE env if needed.
    try:
        DATABASES["default"]["CONN_MAX_AGE"] = int(os.getenv("CONN_MAX_AGE", "0"))
    except Exception:
        DATABASES["default"]["CONN_MAX_AGE"] = 0
    # Avoid server-side cursors when behind transaction poolers
    DATABASES["default"]["DISABLE_SERVER_SIDE_CURSORS"] = True
else:
    # In production we require DATABASE_URL; fail fast to avoid silent SQLite fallback
    raise RuntimeError("DATABASE_URL must be set in production")


LANGUAGE_CODE = "en-us"
TIME_ZONE = os.getenv("TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True


STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
# Only include static directories that actually exist in the current runtime
_static_candidates = [
    BASE_DIR / "static",
    BASE_DIR.parent.parent / "FE" / "dist",  # React frontend build (FE folder)
]
STATICFILES_DIRS = [p for p in _static_candidates if p.exists()]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Media subfolders
MEDIA_EXAMS_DIR = MEDIA_ROOT / "exams"
MEDIA_QUESTIONS_DIR = MEDIA_ROOT / "questions"
MEDIA_SUBMISSIONS_DIR = MEDIA_ROOT / "submissions"
MEDIA_ANSWERS_DIR = MEDIA_ROOT / "answers"
MEDIA_EXPORTS_DIR = MEDIA_ROOT / "exports"

# Create directories on startup (safe if already exists)
for _d in [
    MEDIA_ROOT,
    MEDIA_EXAMS_DIR,
    MEDIA_QUESTIONS_DIR,
    MEDIA_SUBMISSIONS_DIR,
    MEDIA_ANSWERS_DIR,
    MEDIA_EXPORTS_DIR,
]:
    os.makedirs(_d, exist_ok=True)

# Upload limits and formats
MAX_IMAGE_SIZE_MB = float(os.getenv("MAX_IMAGE_SIZE_MB", "50"))
MAX_PDF_SIZE_MB = float(os.getenv("MAX_PDF_SIZE_MB", "20"))
SUPPORTED_IMAGE_FORMATS = ["png", "jpg", "jpeg"]
SUPPORTED_FILE_FORMATS = ["png", "jpg", "jpeg", "pdf"]


REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.BasicAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
}


# Channels – use Redis in production if CHANNEL_REDIS_URL is provided; fallback to in-memory for dev
_channel_redis_url = os.getenv("CHANNEL_REDIS_URL")
if _channel_redis_url:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {"hosts": [_channel_redis_url]},
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# CORS
CORS_ALLOW_ALL_ORIGINS = True
CORS_ALLOW_CREDENTIALS = True

# CSRF Trusted Origins
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:8080",
    "http://127.0.0.1:8080",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8081",
    "http://127.0.0.1:8081",
]

# AI API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash")


# Feature flags
# Do not start grading automatically when a new submission item is created.
# Can be overridden via environment variable AUTO_GRADE_ON_CREATE=true
AUTO_GRADE_ON_CREATE = os.getenv("AUTO_GRADE_ON_CREATE", "false").lower() == "true"

# Grading concurrency settings
# Max concurrent grading API calls per submission (to avoid overwhelming Gemini API)
# For 3-4 concurrent users, total concurrent calls = users * MAX_CONCURRENT_GRADING
# Gemini Flash can handle high concurrency, but 10 per submission is safe
MAX_CONCURRENT_GRADING = int(os.getenv("MAX_CONCURRENT_GRADING", "10"))


# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "%(asctime)s [%(levelname)s] %(name)s %(message)s",
        }
    },
    "handlers": {
        "grading_file": {
            "class": "logging.FileHandler",
            "level": "DEBUG",
            "filename": str(BASE_DIR / "grading.log"),
            "formatter": "verbose",
            "encoding": "utf-8",
        },
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "verbose",
        },
    },
    "loggers": {
        "grading": {
            "handlers": ["grading_file", "console"],
            "level": "DEBUG",
            "propagate": False,
        }
    },
}
