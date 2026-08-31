import os

from .base import *  # noqa: F401,F403


def _flag(name, default):
    return os.environ.get(name, str(default)).lower() in {'1', 'true', 'yes', 'on'}


DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']


# Celery
#
# Tasks run inline in the calling process, so `./manage.py runserver` on its own
# needs no broker and no worker. `compose.yaml` sets CELERY_TASK_ALWAYS_EAGER=0
# for the app containers, since that stack does have a real Redis and worker.
CELERY_TASK_ALWAYS_EAGER = _flag('CELERY_TASK_ALWAYS_EAGER', True)

# Let task exceptions surface in the caller instead of being swallowed into a
# failed result nobody reads.
CELERY_TASK_EAGER_PROPAGATES = _flag('CELERY_TASK_EAGER_PROPAGATES', True)

# Write eager results to the django-db backend anyway, so AsyncResult(...) and
# the admin behave the same as they do against a real worker.
CELERY_TASK_STORE_EAGER_RESULT = _flag('CELERY_TASK_STORE_EAGER_RESULT', True)
