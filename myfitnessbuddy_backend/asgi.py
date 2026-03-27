"""
ASGI config for myfitnessbuddy_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
import users.routing
import notifications.routing
from users.middleware import TokenAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myfitnessbuddy_backend.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(
        URLRouter(
            users.routing.websocket_urlpatterns + notifications.routing.websocket_urlpatterns
        )
    ),
})
