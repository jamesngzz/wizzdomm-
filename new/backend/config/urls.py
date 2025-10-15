from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from . import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.exams.urls")),
    path("api/", include("apps.submissions.urls")),
]

# Serve static and media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    # Serve React assets from /assets/ path (Vite build output) if present
    try:
        dist_root = None
        for p in getattr(settings, 'STATICFILES_DIRS', []):
            candidate = p / 'assets'
            if candidate.exists():
                dist_root = candidate
                break
        if dist_root:
            urlpatterns += static('/assets/', document_root=dist_root)
            # Serve React frontend for all other routes (catch-all, but exclude API routes)
            urlpatterns += [re_path(r'^(?!api/).*$', views.serve_frontend)]
    except Exception:
        pass


