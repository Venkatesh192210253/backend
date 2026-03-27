from users.models import FriendRequest

def social_context(request):
    if request.user.is_authenticated:
        pending_count = FriendRequest.objects.filter(receiver=request.user, status='pending').count()
        return {
            'pending_friend_requests_count': pending_count
        }
    return {
        'pending_friend_requests_count': 0
    }
