"""Placeholder tasks that just sleep, to exercise the two worker lanes.

Short tasks (< 5s) run on the `default` queue. Slow ones (10-20s) declare
`queue='automations'` on the decorator, so they run on worker_automations and
cannot tie up the fast lane. The queue lives on the task itself -- there is no
central list to keep in sync.
"""

import logging
import time

from celery import shared_task

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
