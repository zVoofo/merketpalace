from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'catalog'
    verbose_name = 'Каталог'

    def ready(self):
        from pathlib import Path
        from django.conf import settings
        root = Path(settings.MEDIA_ROOT)
        for sub in ('chat', 'listings', 'search_previews', 'avatars', 'org_logos'):
            (root / sub).mkdir(parents=True, exist_ok=True)
