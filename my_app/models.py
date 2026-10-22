from django.db import models
from django.db.models import Q
from django_celery_results.models import TaskResult

# A failed item is retried automatically on each hourly run until it has been
# tried this many times. After that it stays failed until someone retries it
# from the admin.
MAX_ATTEMPTS = 3


class WorkItemQuerySet(models.QuerySet):
    def due(self):
        """Items the next run should work on: new ones, retried ones, and failed
        ones that still have attempts left."""
        return self.filter(
            Q(status=WorkItem.Status.PENDING)
            | Q(status=WorkItem.Status.FAILED, attempts__lt=MAX_ATTEMPTS)
        )


class WorkItem(models.Model):
    """One unit of browser work. create_work_items adds these, and the hourly
    process_work_items task works through them (my_app/tasks.py)."""

    class Status(models.TextChoices):
        PENDING = 'pending'
        RUNNING = 'running'
        DONE = 'done'
        FAILED = 'failed'

    # Whatever the browser work needs to know about this item.
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=10, choices=Status, default=Status.PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    # The process_work_items run that last picked this item up, for debugging.
    # Empty until the first run. Celery deletes old task results (result_expires),
    # which empties this again.
    task_result = models.ForeignKey(
        TaskResult,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='work_items',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    objects = WorkItemQuerySet.as_manager()

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'work item {self.pk} ({self.status})'
