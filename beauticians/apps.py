from django.apps import AppConfig


class BeauticiansConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'beauticians'
    
    def ready(self):
        pass
