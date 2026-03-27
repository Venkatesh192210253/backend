import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope['url_route']['kwargs']['user_id']
        self.group_name = f"user_{self.user_id}"

        # Get the authenticated user from the scope
        user = self.scope.get('user')

        # Check if user is authenticated and is the same as requested user_id
        if user and user.is_authenticated and str(user.id) == str(self.user_id):
            # Join room group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
        else:
            await self.close()

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            # Leave room group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    # Receive message from room group
    async def notification_message(self, event):
        # Send message to WebSocket with the wrapper expected by the frontend
        await self.send(text_data=json.dumps({
            "type": "notification_message",
            "content": event["content"]
        }))
