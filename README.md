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
s

## Queues

Short tasks run on `default`. Slow automations (5-15 minutes) run on
`automations` with their own worker, so one long job can't occupy every slot the
fast tasks need. Route a task to the slow lane in `CELERY_TASK_ROUTES`
(`mysite/settings/base.py`), or per call with
`my_task.apply_async(queue='automations')`.
