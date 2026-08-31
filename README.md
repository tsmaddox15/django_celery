# django_celery

Django 6.1 + Celery 5.6, with Redis as the broker and task results stored in the
database via `django-celery-results`.

## Running it

```bash
docker compose up --build
```

| Service              | What it runs                          | Where                 |
|----------------------|---------------------------------------|-----------------------|
| `redis`              | broker                                | `localhost:6379`      |
| `web`                | `manage.py migrate`, then `runserver` | http://localhost:8000 |
| `worker`             | `-Q default --concurrency 3`          | —                     |
| `worker_automations` | `-Q automations --concurrency 2`      | —                     |
| `beat`               | `celery -A mysite beat`               | —                     |
| `flower`             | `celery -A mysite flower`             | http://localhost:5555 |

Docker is the dev environment, so tasks always go through Redis to a real
worker. There is no eager mode.

## Queues

Short tasks run on `default`. Slow automations (5-15 minutes) run on
`automations` with their own worker, so one long job can't occupy every slot the
fast tasks need. Route a task to the slow lane in `CELERY_TASK_ROUTES`
(`mysite/settings/base.py`), or per call with
`my_task.apply_async(queue='automations')`.

`CELERY_WORKER_PREFETCH_MULTIPLIER = 1` matters here: at the default of 4, each
child reserves 4 tasks up front, so one worker claims a backlog it won't start
for an hour while other workers sit idle and can't take them.

Check the wiring end to end:

```bash
docker compose exec web python manage.py shell -c "
from mysite.celery import add, long_running
print(add.delay(21, 21).get(timeout=30))
print(long_running.delay(5).get(timeout=60))
"
```

## Notes

- The source tree is bind-mounted with `:z` for SELinux, and the containers run
  as a non-root `app` user (Celery's worker refuses to run as root). Set `UID`
  and `GID` at build time to match your host user.
- `container_name` is a Docker-wide namespace, so every name here is prefixed
  `django_` to avoid colliding with the `redis` and `celery_flower` containers
  in `fastapi_playground`. The two stacks still share ports 6379/8000/5555, so
  only run one at a time.
- Tasks are acked on receipt (`task_acks_late` is off), so a worker restart
  loses whatever was mid-flight. For a 15-minute automation that is a real
  window; add `@app.task(acks_late=True)` to any task that is safe to run twice.
- `django-celery-beat` is **not** installed: its newest release caps at
  `Django < 6.1`. Beat therefore uses Celery's own `PersistentScheduler`, with
  the schedule file on the `beat-schedule` volume, and periodic tasks are
  defined in `CELERY_BEAT_SCHEDULE` rather than in the database. Swap in
  `django-celery-beat` once it supports Django 6.1.
