from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from .models import Notification
from .serializers import NotificationSerializer

def send_notification(user_id, title, message, type='AIRecommendation'):
    # 1. Save notification in database
    notification = Notification.objects.create(
        user_id=user_id,
        title=title,
        message=message,
        type=type
    )

    # 2. Prepare data for WebSocket
    channel_layer = get_channel_layer()
    group_name = f"user_{user_id}"
    
    serializer = NotificationSerializer(notification)
    
    # 3. Send notification through WebSocket
    async_to_sync(channel_layer.group_send)(
        group_name,
        {
            "type": "notification_message",
            "content": serializer.data
        }
    )
    
    return notification
