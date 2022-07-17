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
        text_data_json = json.loads(text_data)
        # message = text_data_json['message']
        _type = text_data_json['type']
        # new_message = Message(user=self.scope['user'], reply_id=message['reply'], text=message['text'], chat=self.chat)
        # new_message.save()
        # # for media in message['media']:
        # #     file = ContentFile(b64decode(media['b']), media['filename'])
        # #     new_message.media.create(file=file)
        # serializer = MessageSerializer(new_message)
        # new_text_data = json.dumps(serializer.data, cls=encoders.JSONEncoder, ensure_ascii=False)
        # async_to_sync(self.channel_layer.group_send)(self.room_group_name, {'type': _type, 'message': new_text_data})
        # async_to_sync(self.channel_layer.group_send)(self.room_group_name, {'type': _type, 'message': message})

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

    def new_message(self, event):
        self.send(text_data=event["message"])


