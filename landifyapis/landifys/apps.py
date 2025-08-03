from django.apps import AppConfig

class LandifysConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'landifys'

    def ready(self):
        # Import file signals để các decorator @receiver được đăng ký.
        import landifys.signals
