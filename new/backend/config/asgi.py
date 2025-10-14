import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path
from apps.jobs.ws import NotificationConsumer


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")


django_asgi_app = get_asgi_application()


websocket_urlpatterns = [
    path("ws/notifications/", NotificationConsumer.as_asgi()),
]

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": URLRouter(websocket_urlpatterns),
})


