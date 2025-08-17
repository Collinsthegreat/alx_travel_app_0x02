from .celery import app as celery_app  # Why: ensure Celery auto-discovery on Django start
__all__ = ("celery_app",)