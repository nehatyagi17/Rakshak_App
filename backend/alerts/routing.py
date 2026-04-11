from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/safety/', consumers.SafetyConsumer.as_asgi()),
    path('ws/authority/', consumers.AuthorityConsumer.as_asgi()),
]
