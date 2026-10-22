# Why beat uses a custom scheduler on SQL Server

`celery beat` in this project runs through `mysite/schedulers.py` rather than
django-celery-beat's own `DatabaseScheduler`. This page explains the bug it works
around, what the fix changes, and how to reuse it in another project.

Versions this was found and fixed on: Django 5.2.18, django-celery-beat 2.9.0,
mssql-django 2.0.0, Microsoft ODBC Driver 17, SQL Server 2022.

## The symptom

Beat crashes on startup, before it sends anything:

```
beat raised exception <class 'django.db.utils.DataError'>:
DataError('22018', "[22018] [Microsoft][ODBC Driver 17 for SQL Server][SQL Server]
Conversion failed when converting the nvarchar value '*' to data type int. (245) (SQLFetch)")
```

The value in quotes varies (`'*'`, `'*/2'`, `'9-17'`, `'('` …). It is the `hour`
of one of the crontab schedules in the database.

It appears as soon as **any** row in `django_celery_beat_crontabschedule` has an
hour that isn't a plain number. That row doesn't have to belong to an enabled
task, or to any task. Here, it started with the hourly schedule
`crontab(minute=0)`, whose hour is `*`.

## The cause

Each time beat loads its schedule, django-celery-beat 2.9.0 tries to skip crontab
tasks that can't be due soon. In `DatabaseScheduler._get_crontab_exclude_query()`
it:

1. selects crontab schedules whose `hour` is a plain number (`"0"`–`"23"`)
2. casts that `hour` column to an integer and shifts it for the schedule's time zone
3. excludes tasks whose hour is more than two hours away from the current hour

Steps 1 and 2 become a single SQL query, roughly:

```sql
SELECT id FROM django_celery_beat_crontabschedule
WHERE hour IN ('0', '1', ..., '23')
  AND NOT (CAST(hour AS int) /* + tz offset */ % 24 IN (19, 20, 21, 22, 23, 4))
```

The code assumes the database applies `hour IN (...)` first, so the `CAST` only
ever sees numbers. **SQL Server makes no such promise.** Its optimizer may
evaluate the conditions in any order, so it can run `CAST('*' AS int)` on a row
the first condition would have removed, and that cast is an error.

The library is mainly used with PostgreSQL and SQLite. SQLite never fails a
`CAST`: it turns non-numeric text into `0`. So this ordering assumption rarely
causes problems outside SQL Server.

## The fix

`mysite/schedulers.py` subclasses the stock scheduler and replaces that one
method:

```python
class DatabaseScheduler(BaseDatabaseScheduler):
    def _get_crontab_exclude_query(self):
        return Q(pk__in=[])
```

`Q(pk__in=[])` is a condition that matches nothing, so no crontab task gets
excluded and the `CAST` query is never built. The query beat now runs is just:

```sql
WHERE enabled = 1
  AND NOT (clocked_time > <now + 5 minutes> AND clocked_id IS NOT NULL)
```

The exclusion of one-off ("clocked") tasks that aren't due within five minutes
is unchanged.

Settings point beat at the subclass:

```python
# mysite/settings/base.py
CELERY_BEAT_SCHEDULER = 'mysite.schedulers:DatabaseScheduler'
```

## What this changes, and what it doesn't

- **Same:** when tasks run. Beat still checks every enabled task against its own
  schedule before sending it. The removed query only decided which tasks beat
  bothered to *load*, not which ones it *sends*.
- **Same:** editing schedules in the admin, the five-minute sync with the
  database, one-off tasks, and the `CELERY_BEAT_SCHEDULE` entries in settings.
- **Different:** beat loads every enabled task each time it syncs, instead of
  only crontabs near the current hour. That is the speed-up we gave up. It
  matters with thousands of periodic tasks; with dozens or hundreds it makes no
  measurable difference.

## Using it in another project

1. Copy `mysite/schedulers.py` into the package that holds that project's
   `celery.py`.
2. Point the setting at it:
   `CELERY_BEAT_SCHEDULER = '<package>.schedulers:DatabaseScheduler'`.
3. Check beat's `command:` in `docker-compose.yml`. A `-S` or `--scheduler
   django_celery_beat.schedulers:DatabaseScheduler` flag overrides the setting.
   Remove it, or point it at the subclass.
4. Restart beat and look at the top of its log. It should say
   `. scheduler -> <package>.schedulers.DatabaseScheduler`.

## When upgrading django-celery-beat

`_get_crontab_exclude_query` is a private method, so a new release can rename or
remove it without notice. If it does, the override silently stops doing anything
and the crash can come back. After an upgrade:

1. Check that the method still exists and is still where the `CAST` happens:
   `grep -n "_get_crontab_exclude_query\|Cast(" <site-packages>/django_celery_beat/schedulers.py`
2. Read the release notes. If they say this query was fixed for SQL Server or
   other databases, delete `mysite/schedulers.py` and set
   `CELERY_BEAT_SCHEDULER` back to
   `'django_celery_beat.schedulers:DatabaseScheduler'`.
3. Either way, restart beat with a crontab schedule whose hour is `*` in the
   database (the hourly `sync-crm-contacts-hourly` entry is one) and confirm it
   starts without the `Conversion failed` error.
