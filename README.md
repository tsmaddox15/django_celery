# django_celery

Django 5.2 + Celery 5.6, with Redis as the broker, SQL Server 2022 as the
database, task results stored in it via `django-celery-results`, and the beat
schedule stored in it via `django-celery-beat`.

## Running it

```bash
docker compose up --build
```

| Service              | What it runs                          | Where                 |
|----------------------|---------------------------------------|-----------------------|
| `redis`              | broker                                | `localhost:6379`      |
| `mssql`              | SQL Server 2022 (Developer edition)   | `localhost:1433`      |
| `mssql-init`         | one-shot: creates the `mysite` DB     | —                     |
| `migrate`            | one-shot: `manage.py migrate`         | —                     |
| `web`                | `manage.py runserver`                 | http://localhost:8000 |
| `worker`             | `-Q default --concurrency 3`          | —                     |
| `worker_automations` | `-Q automations --concurrency 2`      | —                     |
| `beat`               | `celery -A mysite beat` (DB schedule) | —                     |
| `flower`             | `celery -A mysite flower`             | http://localhost:5555 |

## Database

Inside compose, Django talks to SQL Server through `mssql-django` and Microsoft's
ODBC Driver 17 (installed in the `Dockerfile`). The `sa` password defaults to a
dev-only value; set `MSSQL_SA_PASSWORD` in `.env` to change it.

Without `ADMIN_HOST` set (e.g. running `manage.py` straight on the host), settings
fall back to SQLite. To point a host-run Django at the container instead, install
`msodbcsql17` on the host and export `ADMIN_HOST=localhost`, `ADMIN_PASSWORD=...` and
`ADMIN_EXTRA_PARAMS=TrustServerCertificate=yes`.

## Queues

Short tasks run on `default`. Slow automations (5-15 minutes) run on
`automations` with their own worker, so one long job can't occupy every slot the
fast tasks need. Route a task to the slow lane in `CELERY_TASK_ROUTES`
(`mysite/settings/base.py`), or per call with
`my_task.apply_async(queue='automations')`.

## Periodic tasks (beat)

The schedule lives in SQL Server, in `django-celery-beat`'s tables. Add, edit,
pause or delete tasks in the admin under **Periodic Tasks**; beat notices
changes within a few seconds, without a restart.

Schedules can also be written in code in `CELERY_BEAT_SCHEDULE`
(`mysite/settings/base.py`). Beat copies those into the database every time it
starts, overwriting admin edits to them; removing one from settings does not
delete its row, so disable or delete it in the admin too.

Beat runs through `mysite/schedulers.py`, a small subclass of
`django-celery-beat`'s `DatabaseScheduler`. The stock one runs a query that SQL
Server rejects as soon as any crontab has a non-numeric hour like `*`.

Run exactly one beat process; two would send every task twice.
