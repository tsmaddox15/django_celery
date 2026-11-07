from django.contrib import admin
from django_celery_results.admin import GroupResultAdmin
from django_celery_results.models import GroupResult

from .models import TaskItem
from .tasks import send_task_items

# Celery states in which a task may still run, so sending it again would double it.
IN_PROGRESS = ['PENDING', 'STARTED', 'RETRY']


def last_error(item):
    # The last line of the traceback, e.g. "ValueError: /nope/ not found".
    traceback = item.task_result and item.task_result.traceback
    return traceback.strip().splitlines()[-1] if traceback else ''


@admin.register(TaskItem)
class TaskItemAdmin(admin.ModelAdmin):
    list_display = ['pk', 'payload', 'status', last_error, 'group_result', 'created_at']
    list_filter = ['task_result__status']
    list_select_related = ['task_result', 'group_result']
    readonly_fields = ['task_result', 'group_result', 'created_at']
    actions = ['send_again']

    @admin.display(ordering='task_result__status')
    def status(self, item):
        return item.task_result.status if item.task_result else 'not sent'

    @admin.action(description='Send again, as a new group')
    def send_again(self, request, queryset):
        items = queryset.exclude(task_result__status__in=IN_PROGRESS)
        if not items:
            self.message_user(request, 'Nothing to send: the selected items are still in progress.')
            return
        group_id = send_task_items(items)
        self.message_user(request, f'Sent {len(items)} items as group {group_id}.')


class TaskItemInline(admin.TabularInline):
    model = TaskItem
    fields = ['payload', 'status', last_error, 'task_result']
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False

    def status(self, item):
        return item.task_result.status if item.task_result else ''


# django_celery_results' own Group results page, plus the items sent in each group.
admin.site.unregister(GroupResult)


@admin.register(GroupResult)
class GroupResultWithTaskItemsAdmin(GroupResultAdmin):
    inlines = [TaskItemInline]
