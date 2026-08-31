import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'mysite.settings.dev')

app = Celery('mysite')

# Pull every CELERY_* name out of Django settings, so configuration lives in
# mysite/settings/ rather than here.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load tasks.py from each app in INSTALLED_APPS.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')


@app.task
def add(x, y):
    """Placeholder task, handy for checking the worker and Flower are wired up."""
    return x + y
