import os

from .base import *  # noqa: F401,F403

DEBUG = False

SECRET_KEY = os.environ['DJANGO_SECRET_KEY']


# Celery
#
# Explicitly off — never let production short-circuit the queue.
CELERY_TASK_ALWAYS_EAGER = False
CELERY_TASK_EAGER_PROPAGATES = False
