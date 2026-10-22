# django_celery

Django 5.2 + Celery 5.6, with Redis as the broker, SQL Server 2022 as the
database, task results stored in it via `django-celery-results`, and the beat
schedule stored in it via `django-celery-beat`.

## Running it

```bash
cp .env.example .env   # first time only; then fill in real values
docker compose up --build
```

| Service              | What it runs                          | Where                 |
|----------------------|---------------------------------------|-----------------------|
| `redis`              | broker                                | `localhost:6379`      |
| `mssql`              | SQL Server 2022 (Developer edition)   | `localhost:1433`      |
| `mssql-init`         | one-shot: creates the `DB_NAME` DB    | —                     |
| `migrate`            | one-shot: `manage.py migrate`         | —                     |
| `web`                | `manage.py runserver`                 | http://localhost:8000 |
| `worker`             | `-Q default --concurrency 2`          | —                     |
| `worker_automations` | `-Q automations --concurrency 3`      | —                     |
| `beat`               | `celery -A mysite beat` (DB schedule) | —                     |
| `flower`             | `celery -A mysite flower`             | http://localhost:5555 |
| `selenium`           | Chrome for browser automations        | http://localhost:7900 (noVNC, password `secret`) |

## Settings and secrets (`.env`)

All configuration lives in `.env`, which is git-ignored and kept out of the
image by `.dockerignore`. `.env.example` lists every key. Each service built
from this repo (web, both workers, beat, flower, migrate) loads the whole file
through `env_file`, so a variable you add there is visible to all of them as
`os.environ['NAME']`. Run `docker compose up -d` after editing `.env`; a plain
`docker restart` keeps the old values.

Wrap values containing `$` or `#` in single quotes, or Compose will expand or
strip them. To see what a service actually receives:
`docker compose exec worker env`.

## Database

Inside compose, Django talks to SQL Server through `mssql-django` and Microsoft's
ODBC Driver 17 (installed in the `Dockerfile`). The app logs in as `sa`, so
`DB_PASSWORD` in `.env` is also the `sa` password the `mssql` container is
created with. SQL Server only reads it the first time the `mssql_data` volume is
created; to change it afterwards, run `docker compose down -v` (which deletes the
database) or change the login's password in SQL Server too.

Without `DB_HOST` set (e.g. running `manage.py` straight on the host), settings
fall back to SQLite. To point a host-run Django at the container instead, install
`msodbcsql17` on the host and export `DB_HOST=localhost`, `DB_PASSWORD=...` and
`DB_EXTRA_PARAMS=TrustServerCertificate=yes`.

## Queues

Short tasks run on `default`. Slow automations (5-15 minutes) run on
`automations` with their own worker, so one long job can't occupy every slot the
fast tasks need. Route a task to the slow lane in `CELERY_TASK_ROUTES`
(`mysite/settings/base.py`), or per call with
`my_task.apply_async(queue='automations')`.

## Browser automations (work items)

Browser work is split into small units, each a `WorkItem` row
(`my_app/models.py`) with a status, an attempt count and the last error:

1. `create_work_items(payloads)` adds one pending item per payload. The payload
   is whatever the browser work needs to know about that item.
2. `process_work_items` runs every hour from beat. It opens one browser in the
   `selenium` container, logs in once, and works through the due items one at a
   time, marking each `done` or `failed`. It stops starting new items after 20
   minutes, leaving the rest for the next hour.

Track the items in the admin under **Work items**, filtered by status. A failed
item is retried on each hourly run until it has had 3 attempts
(`MAX_ATTEMPTS`); after that, select it and use **Retry on the next run**. To
run without waiting for the hour, use **Run selected tasks** on
`process-work-items-hourly` under **Periodic Tasks**.

If the login fails, the run fails before touching any item, so nothing is
marked failed. An item left `running` by a killed worker is marked failed at the
start of the next run, so it gets retried.

To point it at a real site, set `AUTOMATION_SITE_*` in `.env`, and change
`log_in()` in `my_app/browser.py` and `process_item()` in `my_app/tasks.py`.
They currently log in to this project's own admin and open the page in each
item's `path`.

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
Server rejects as soon as any crontab has a non-numeric hour like `*`; see
[docs/beat-scheduler-sql-server.md](docs/beat-scheduler-sql-server.md).

Run exactly one beat process; two would send every task twice.
