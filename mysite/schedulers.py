from django.db.models import Q
from django_celery_beat.schedulers import DatabaseScheduler as BaseDatabaseScheduler


class DatabaseScheduler(BaseDatabaseScheduler):
    """django-celery-beat's scheduler, made to work on SQL Server.

    To skip crontab tasks that can't be due soon, the base class runs
    CAST(hour AS int) on rows it has already filtered to numeric hours. SQL
    Server doesn't promise to filter before it casts, so a crontab with
    hour='*' fails with "Conversion failed when converting the nvarchar value
    '*' to data type int". That filter only saves work on schedules with
    thousands of entries, so drop it: beat still checks every enabled task's
    own schedule before sending it.
    """

    def _get_crontab_exclude_query(self):
        return Q(pk__in=[])
