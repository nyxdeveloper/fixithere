import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "fixithere.settings")

import django
from django.conf import settings
from django.urls import path

if not settings.configured:
    django.setup()

from .middleware import TokenAuthMiddleware
from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from api import consumers

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(
        URLRouter([
            path('ws/chats/<int:pk>/', consumers.ChatConsumer.as_asgi()),
        ])
    ),
})
