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
    # Serve React assets from /assets/ path (Vite build output)
    urlpatterns += static('/assets/', document_root=settings.STATICFILES_DIRS[1] / 'assets')
    # Serve React frontend for all other routes (catch-all, but exclude API routes)
    urlpatterns += [re_path(r'^(?!api/).*$', views.serve_frontend)]


