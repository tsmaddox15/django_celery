"""Placeholder tasks that just sleep, to exercise the two worker lanes.

Short tasks (< 5s) run on the `default` queue. Slow ones (10-20s) declare
`queue='automations'` on the decorator, so they run on worker_automations and
cannot tie up the fast lane. The queue lives on the task itself -- there is no
central list to keep in sync.

At the bottom, the work-item tasks: real browser work, tracked per item.
"""

import logging
import time
import traceback
from datetime import timedelta

from celery import shared_task
from celery.exceptions import SoftTimeLimitExceeded
from django.conf import settings
from django.utils import timezone
from django_celery_results.models import TaskResult

from .browser import log_in, new_driver
from .models import WorkItem

logger = logging.getLogger(__name__)


# --- short tasks: default queue ------------------------------------------


@shared_task(bind=True)
def send_notification_email(self, user_id, seconds=2):
    logger.info('sending notification to user %s on %s', user_id, self.request.hostname)
    time.sleep(seconds)
    return f'emailed user {user_id}'


@shared_task(bind=True)
def generate_thumbnail(self, image_id, seconds=3):
    logger.info('thumbnailing image %s on %s', image_id, self.request.hostname)
    time.sleep(seconds)
    return f'thumbnailed image {image_id}'


@shared_task(bind=True)
def refresh_dashboard_cache(self, seconds=1):
    logger.info('refreshing dashboard cache on %s', self.request.hostname)
    time.sleep(seconds)
    return 'dashboard cache refreshed'


@shared_task(bind=True)
def validate_upload(self, upload_id, seconds=4):
    logger.info('validating upload %s on %s', upload_id, self.request.hostname)
    time.sleep(seconds)
    return f'upload {upload_id} valid'


# --- long automations: automations queue ---------------------------------


@shared_task(bind=True, queue='automations')
def sync_crm_contacts(self, seconds=15):
    logger.info('syncing CRM contacts on %s', self.request.hostname)
    time.sleep(seconds)
    return f'synced CRM contacts in {seconds}s'


@shared_task(bind=True, queue='automations')
def rebuild_search_index(self, seconds=12):
    logger.info('rebuilding search index on %s', self.request.hostname)
    time.sleep(seconds)
    return f'rebuilt search index in {seconds}s'


@shared_task(bind=True, queue='automations')
def generate_monthly_report(self, month, seconds=20):
    logger.info('generating report for %s on %s', month, self.request.hostname)
    time.sleep(seconds)
    return f'report for {month} ready'


@shared_task(bind=True, queue='automations')
def import_vendor_catalog(self, vendor_id, seconds=18):
    logger.info('importing catalog for vendor %s on %s', vendor_id, self.request.hostname)
    time.sleep(seconds)
    return f'imported catalog for vendor {vendor_id}'


# --- work items: created up front, worked through hourly -----------------
# create_work_items adds one WorkItem row per piece of work. Every hour,
# process_work_items logs in once and works through the due items, recording
# each one's result, so failures can be seen and redone from the admin.

# Stop starting new items after this long, so a run ends well inside
# CELERY_TASK_SOFT_TIME_LIMIT (25 min). Whatever is left waits for the next run.
RUN_BUDGET = 20 * 60


@shared_task
def create_work_items(payloads):
    """Add one pending WorkItem per payload, for the next hourly run."""
    WorkItem.objects.bulk_create(WorkItem(payload=payload) for payload in payloads)
    return f'created {len(payloads)} work items'


def process_item(driver, item):
    """The browser work for one item. Raise to mark the item failed.

    The example opens the page named in the payload and fails on a 404.
    """
    driver.get(settings.AUTOMATION_SITE_URL + item.payload['path'])
    if 'Page not found' in driver.title:
        raise ValueError(f"{item.payload['path']} not found")


def _fail_interrupted_items():
    # A run killed outright (hard time limit, worker restart) leaves its item
    # marked running. Once it is older than any run can last, count it as failed.
    cutoff = timezone.now() - timedelta(seconds=settings.CELERY_TASK_TIME_LIMIT)
    WorkItem.objects.filter(status=WorkItem.Status.RUNNING, updated_at__lt=cutoff).update(
        status=WorkItem.Status.FAILED,
        last_error='interrupted: the run working on it was killed',
        updated_at=timezone.now(),
    )


@shared_task(bind=True, queue='automations')
def process_work_items(self):
    """Hourly: log in once, then work through every due item one at a time."""
    _fail_interrupted_items()
    ids = list(WorkItem.objects.due().values_list('pk', flat=True))
    if not ids:
        return 'no work items due'

    deadline = time.monotonic() + RUN_BUDGET
    counts = {WorkItem.Status.DONE: 0, WorkItem.Status.FAILED: 0}
    # This run's own result row, so each item can point back to it. The worker
    # normally creates it already (CELERY_TASK_TRACK_STARTED); the result backend
    # updates the same row when the run ends.
    task_result, _ = TaskResult.objects.get_or_create(task_id=self.request.id)
    driver = new_driver()
    try:
        # If the login fails, the task fails here and every item stays as it was.
        log_in(driver)
        for pk in ids:
            if time.monotonic() > deadline:
                break
            # Claim the item, so a second run started at the same time skips it.
            if not WorkItem.objects.due().filter(pk=pk).update(
                status=WorkItem.Status.RUNNING, task_result=task_result, updated_at=timezone.now()
            ):
                continue
            item = WorkItem.objects.get(pk=pk)
            try:
                process_item(driver, item)
            except SoftTimeLimitExceeded:
                # Out of time mid-item: not the item's fault, so it goes back to pending.
                item.status = WorkItem.Status.PENDING
                item.save()
                raise
            except Exception:
                logger.exception('work item %s failed', pk)
                item.status = WorkItem.Status.FAILED
                item.last_error = traceback.format_exc()
            else:
                item.status = WorkItem.Status.DONE
                item.last_error = ''
                item.finished_at = timezone.now()
            item.attempts += 1
            item.save()
            counts[item.status] += 1
    finally:
        driver.quit()

    left = len(ids) - sum(counts.values())
    return f'{counts[WorkItem.Status.DONE]} done, {counts[WorkItem.Status.FAILED]} failed, {left} left for the next run'
