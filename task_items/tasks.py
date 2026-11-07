"""Browser work run as one Celery task per item, for comparison with my_app.

Every hour, send_new_task_items sends the items not sent yet as one Celery
group. Each item's process_task_item task does the browser work in its worker
process's logged-in session (sessions.py). Errors aren't caught: a failing task
is retried by Celery, and its last failure and traceback are kept in its
TaskResult.
"""

from celery import group, shared_task
from django.conf import settings
from django_celery_results.models import GroupResult, TaskResult

from .models import TaskItem
from .sessions import browser_session


@shared_task(bind=True, queue='automations', autoretry_for=(Exception,), max_retries=2, retry_backoff=10)
def process_task_item(self, pk):
    """The browser work for one item. The example opens the page named in the
    payload and fails on a 404."""
    item = TaskItem.objects.get(pk=pk)
    with browser_session() as driver:
        driver.get(settings.AUTOMATION_SITE_URL + item.payload['path'])
        if 'Page not found' in driver.title:
            raise ValueError(f"{item.payload['path']} not found")
        return driver.title


def send_task_items(items):
    """Send items as one group of process_task_item tasks, linking each item to
    its new task and the group. Returns the group id."""
    items = list(items)
    job = group(process_task_item.s(item.pk) for item in items)
    # freeze() picks the group and task ids before anything is sent, so the
    # links exist before any worker starts on the tasks.
    result = job.freeze()
    result.save()
    group_result = GroupResult.objects.get(group_id=result.id)
    for item, task in zip(items, result.results):
        # The result backend fills in this same row as the task runs.
        item.task_result = TaskResult.objects.create(
            task_id=task.id, task_name=process_task_item.name, status='PENDING'
        )
        item.group_result = group_result
        item.save()
    job.apply_async()
    return result.id


@shared_task
def create_task_items(payloads):
    """Add one TaskItem per payload, for the next hourly send."""
    TaskItem.objects.bulk_create(TaskItem(payload=payload) for payload in payloads)
    return f'created {len(payloads)} task items'


@shared_task
def send_new_task_items():
    """Hourly: send every item not sent yet, as one group."""
    items = list(TaskItem.objects.filter(task_result=None))
    if not items:
        return 'no new task items'
    return f'sent {len(items)} task items as group {send_task_items(items)}'
