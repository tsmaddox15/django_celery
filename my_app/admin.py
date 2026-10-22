from django.contrib import admin
from django.utils import timezone
from django_celery_results.admin import TaskResultAdmin
from django_celery_results.models import TaskResult

from .models import WorkItem


@admin.register(WorkItem)
class WorkItemAdmin(admin.ModelAdmin):
    list_display = ['pk', 'status', 'attempts', 'payload', 'task_result', 'created_at', 'finished_at']
    list_filter = ['status']
    search_fields = ['task_result__task_id']
    readonly_fields = ['status', 'attempts', 'last_error', 'task_result', 'created_at', 'updated_at', 'finished_at']
    actions = ['retry']

    @admin.action(description='Retry on the next run')
    def retry(self, request, queryset):
        # Running items are left alone; their run will set the outcome.
        count = queryset.exclude(status=WorkItem.Status.RUNNING).update(
            status=WorkItem.Status.PENDING, updated_at=timezone.now()
        )
        self.message_user(request, f'{count} items will be retried on the next run.')


class WorkItemInline(admin.TabularInline):
    model = WorkItem
    fields = ['status', 'attempts', 'payload', 'last_error', 'finished_at']
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


# django_celery_results' own Task results page, plus the work items each run handled.
admin.site.unregister(TaskResult)


@admin.register(TaskResult)
class TaskResultWithWorkItemsAdmin(TaskResultAdmin):
    inlines = [WorkItemInline]
