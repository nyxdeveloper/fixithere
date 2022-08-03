from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from rest_framework.utils import json, encoders

from django.core.files.base import ContentFile

# локальные импорты
from .models import Chat
from .models import Message
from .serializers import MessageSerializer

from base64 import b64decode


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_active:
            return self.close()
        try:
            chat = Chat.objects.get(id=self.scope['url_route']['kwargs']['pk'])
            self.chat = chat
            self.room_name = str(chat.id)
            self.room_group_name = 'chat-' + self.room_name
            async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
            self.accept()
        except Chat.DoesNotExist:
            self.close()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)()

    def receive(self, text_data=None, bytes_data=None):
        pass

    def chat_message(self, event):
        self.send(text_data=event["message"])

    def read_messages(self, event):
        self.send(text_data=event["message"])


class UserMessagesConsumer(WebsocketConsumer):
    def connect(self):
        user = self.scope['user']
        if user.is_anonymous or not user.is_active:
            return self.close()
        self.room_name = str(user.id)
        self.room_group_name = 'messages-' + self.room_name
        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)()

    def new_message(self, event):
        self.send(text_data=event["message"])


class SubscriptionPermissionsConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_active:
            return self.close()
        self.room_name = str(self.scope['user'].id)
        self.room_group_name = 'subscription-permissions-' + self.room_name
        async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
        self.accept()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)()

    def change_permissions(self, event):
        self.send(text_data=event["message"])
