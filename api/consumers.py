from asgiref.sync import async_to_sync
from channels.generic.websocket import WebsocketConsumer
from rest_framework.utils import json

# локальные импорты
from .models import Chat


class ChatConsumer(WebsocketConsumer):
    def connect(self):
        if not self.scope['user'].is_active:
            return self.close()
        try:
            chat = Chat.objects.get(id=self.scope['url_route']['kwargs']['pk'])
            self.room_name = str(chat.id)
            self.room_group_name = 'chat_' + self.room_name
            async_to_sync(self.channel_layer.group_add)(self.room_group_name, self.channel_name)
            self.accept()
        except Chat.DoesNotExist:
            self.close()

    def disconnect(self, close_code):
        async_to_sync(self.channel_layer.group_discard)()

    def receive(self, text_data=None, bytes_data=None):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to room group
        async_to_sync(self.channel_layer.group_send)(
            self.room_group_name,
            {
                'type': text_data_json["type"],
                'message': message
            }
        )

    def chat_message(self, event):
        self.send(text_data=event["message"])

    def read_messages(self, event):
        self.send(text_data=event["message"])
