import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from urllib.parse import parse_qs
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser

User = get_user_model()

@database_sync_to_async
def get_user_from_token(token):
    from datetime import datetime
    import os
    from rest_framework_simplejwt.tokens import AccessToken
    log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_debug.log")
    with open(log_file, "a") as f:
        f.write(f"\n[{datetime.now()}] WS AUTH ATTEMPT with token: {token[:10]}...")
    try:
        access_token = AccessToken(token)
        user_id = access_token['user_id']
        user = User.objects.get(id=user_id)
        with open(log_file, "a") as f:
            f.write(f"\n[{datetime.now()}] WS AUTH SUCCESS: {user.username} (ID: {user.id})")
        return user
    except Exception as e:
        with open(log_file, "a") as f:
            f.write(f"\n[{datetime.now()}] WS AUTH ERROR: {str(e)}")
        print(f"WS AUTH ERROR: {e}")
        return AnonymousUser()

class TokenAuthMiddleware:
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        from datetime import datetime
        import os
        log_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ai_debug.log")
        
        query_string = scope.get('query_string', b'').decode('utf-8')
        query_params = parse_qs(query_string)
        token = query_params.get('token', [None])[0]
        
        with open(log_file, "a") as f:
            f.write(f"\n[{datetime.now()}] WS MIDDLEWARE CALLED | Token found: {token is not None}")

        if token:
            scope['user'] = await get_user_from_token(token)
        else:
            scope['user'] = AnonymousUser()
            
        return await self.inner(scope, receive, send)
