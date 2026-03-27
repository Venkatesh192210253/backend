import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        from datetime import datetime
        import os
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_debug.log")
        
        if self.user.is_authenticated:
            self.group_name = f"user_{str(self.user.id)}"
            
            with open(log_file, "a") as f:
                f.write(f"\n[{datetime.now()}] WS CONNECTED: {self.user.username} (Group: {self.group_name})")

            # Join room group
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            
            # Join all groups the user is a part of
            user_groups = await self.get_user_groups()
            for group_id in user_groups:
                await self.channel_layer.group_add(
                    f"group_{group_id}",
                    self.channel_name
                )
            
            await self.accept()
        else:
            with open(log_file, "a") as f:
                f.write(f"\n[{datetime.now()}] WS REJECTED: Anonymous User")
            await self.close()

    @database_sync_to_async
    def get_user_groups(self):
        from .models import GroupMember
        memberships = GroupMember.objects.filter(user=self.user, status='joined')
        return [m.group_id for m in memberships]

    async def disconnect(self, close_code):
        from datetime import datetime
        import os
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_debug.log")
        
        with open(log_file, "a") as f:
            f.write(f"\n[{datetime.now()}] WS DISCONNECTED: {getattr(self.user, 'username', 'Unknown')} (Code: {close_code})")

        if hasattr(self, 'group_name'):
            # Leave room group
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
            
            # Leave all groups
            user_groups = await self.get_user_groups()
            for group_id in user_groups:
                await self.channel_layer.group_discard(
                    f"group_{group_id}",
                    self.channel_name
                )

    async def receive(self, text_data):
        # Not required for now as per instructions
        pass

    async def send_notification(self, event):
        # Send message to WebSocket
        await self.send(text_data=json.dumps(event["message"]))
