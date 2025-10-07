from django.apps import AppConfig


class SecretaryConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "secretary"

# apps.py (or add to models.py)
from django.apps import AppConfig

class SecretaryConfig(AppConfig):
    name = 'secretary'

    #def ready(self):
        #import secretary.signals  
