from django.apps import AppConfig
class C(AppConfig):
    name='apps.accounts'
    default_auto_field='django.db.models.BigAutoField'
    def ready(self): from . import signals  # noqa
