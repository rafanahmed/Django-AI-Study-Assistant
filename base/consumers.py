import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from base.models import StudyGroup, GroupMessage  # Updated import

User = get_user_model()

class StudyGroupConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.group_id = self.scope['url_route']['kwargs']['group_id']
        self.room_group_name = f'study_group_{self.group_id}'

        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_del(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']
        user_id = text_data_json['user_id']
        username = text_data_json['username']
        group_id = text_data_json['group_id']

    # Save message to database
        message_obj = await self.save_message(group_id, user_id, message)

    # Send message to room group
        await self.channel_layer.group_send(
        self.room_group_name,
        {
            'type': 'chat_message',
            'message': message,
            'username': username,
            'user_id': user_id,
            'timestamp': message_obj.created_at.isoformat()  # Include ISO format timestamp
        }
    )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'message': event['message'],
            'username': event['username'],
            'user_id': event['user_id'],
            'timestamp': event['timestamp']
        }))

    @database_sync_to_async
    def save_message(self, group_id, user_id, content):
        group = StudyGroup.objects.get(id=group_id)
        user = User.objects.get(id=user_id)
        return GroupMessage.objects.create(
            group=group,
            sender=user,
            content=content
        )
