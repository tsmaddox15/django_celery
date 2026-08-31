# Make sure the Celery app is created when Django starts, so that the shared
# @shared_task decorator can find it.
from .celery import app as celery_app

__all__ = ('celery_app',)
