# django_celery

Django 6.1 + Celery 5.6, with Redis as the broker, SQL Server 2022 as the
database, and task results stored in it via `django-celery-results`.

## Running it

```bash
docker compose up --build
```

| Service              | What it runs                          | Where                 |
|----------------------|---------------------------------------|-----------------------|
| `redis`              | broker                                | `localhost:6379`      |
| `mssql`              | SQL Server 2022 (Developer edition)   | `localhost:1433`      |
| `mssql-init`         | one-shot: creates the `mysite` DB     | —                     |
| `web`                | `manage.py migrate`, then `runserver` | http://localhost:8000 |
| `worker`             | `-Q default --concurrency 3`          | —                     |
| `worker_automations` | `-Q automations --concurrency 2`      | —                     |
| `beat`               | `celery -A mysite beat`               | —                     |
| `flower`             | `celery -A mysite flower`             | http://localhost:5555 |

## Database

Inside compose, Django talks to SQL Server through `mssql-django` and Microsoft's
ODBC Driver 18 (installed in the `Dockerfile`). The `sa` password defaults to a
dev-only value; set `MSSQL_SA_PASSWORD` in `.env` to change it.

Without `DB_HOST` set (e.g. running `manage.py` straight on the host), settings
fall back to SQLite. To point a host-run Django at the container instead, install
`msodbcsql18` on the host and export `DB_HOST=localhost`, `DB_PASSWORD=...` and
`DB_EXTRA_PARAMS=TrustServerCertificate=yes`.

## Queues

Short tasks run on `default`. Slow automations (5-15 minutes) run on
`automations` with their own worker, so one long job can't occupy every slot the
fast tasks need. Route a task to the slow lane in `CELERY_TASK_ROUTES`
(`mysite/settings/base.py`), or per call with
`my_task.apply_async(queue='automations')`.
