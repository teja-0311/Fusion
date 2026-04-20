"""
RSPC Module - Application Configuration
"""

from django.apps import AppConfig


class RspcConfig(AppConfig):
    """RSPC application configuration"""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'applications.rspc'
    verbose_name = 'Research & Sponsored Projects Cell'
    
    def ready(self):
        """Import signals when app is ready"""
        try:
            import applications.rspc.signals  # noqa
        except ImportError:
            pass