# accounts/backends.py

from django.contrib.auth.backends import ModelBackend
from .models import ParentUser

class ParentUserBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = ParentUser.objects.get(username=username)
            if user.check_password(password):
                print(f"Authenticated ParentUser: {user}")  # Debugging line
                return user
        except ParentUser.DoesNotExist:
            print(f"ParentUser not found: {username}")  # Debugging line
            return None

    def get_user(self, user_id):
        try:
            return ParentUser.objects.get(pk=user_id)
        except ParentUser.DoesNotExist:
            return None
