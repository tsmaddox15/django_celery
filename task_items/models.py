from django.db import models
from django_celery_results.models import GroupResult, TaskResult


class TaskItem(models.Model):
    """One unit of browser work, run as its own Celery task (task_items/tasks.py).

    Unlike my_app's WorkItem, an item keeps no status of its own: its state,
    retries and traceback are those of the TaskResult it points at.
    """

    # Whatever the browser work needs to know about this item.
    payload = models.JSONField(default=dict)
    # The item's latest task, and the group it was sent in. Empty until sent.
    task_result = models.ForeignKey(
        TaskResult, null=True, blank=True, on_delete=models.SET_NULL, related_name='task_items'
    )
    group_result = models.ForeignKey(
        GroupResult, null=True, blank=True, on_delete=models.SET_NULL, related_name='task_items'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f'task item {self.pk}'
