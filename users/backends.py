from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()

class PlaintextAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Check by email or username
            user = User.objects.filter(email=username).first()
            if not user:
                user = User.objects.filter(username=username).first()
                
            if user and user.password == password:
                return user
        except User.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
