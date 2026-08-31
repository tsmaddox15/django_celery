# django_celery

Django 6.1 + Celery 5.6, with Redis as the broker and task results stored in the
database via `django-celery-results`.

## Running locally (no Docker)

`mysite.settings.dev` sets `CELERY_TASK_ALWAYS_EAGER = True`, so tasks execute
inline in the calling process — no broker or worker needed:

```bash
uv run python manage.py migrate
uv run python manage.py runserver
```

Eager results are still written to the `django-db` backend
(`CELERY_TASK_STORE_EAGER_RESULT`), so `AsyncResult(...)` and the admin behave
the same as they do against a real worker, and exceptions propagate to the
caller (`CELERY_TASK_EAGER_PROPAGATES`).

## Running with Docker Compose

```bash
docker compose build --build-arg UID=$(id -u) --build-arg GID=$(id -g)
docker compose up
```

| Service  | What it runs                              | Where                 |
|----------|-------------------------------------------|-----------------------|
| `redis`  | broker                                    | `localhost:6379`      |
| `web`    | `manage.py migrate`, then `runserver`     | http://localhost:8000 |
| `worker` | `celery -A mysite worker`                 | —                     |
| `beat`   | `celery -A mysite beat`                   | —                     |
| `flower` | `celery -A mysite flower`                 | http://localhost:5555 |

The stack has a real broker and worker, so `web` and `worker` set
`CELERY_TASK_ALWAYS_EAGER=0` — otherwise the worker and Flower would sit idle
while `web` ran everything itself. Drop that variable to get eager behaviour
inside Compose too.

Check the wiring end to end:

```bash
docker compose exec web python -c "
import django; django.setup()
from mysite.celery import add
print(add.delay(21, 21).get(timeout=30))
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
- `django-celery-beat` is **not** installed: its newest release caps at
  `Django < 6.1`. Beat therefore uses Celery's own `PersistentScheduler`, with
  the schedule file on the `beat-schedule` volume, and periodic tasks are
  defined in `CELERY_BEAT_SCHEDULE` rather than in the database. Swap in
  `django-celery-beat` once it supports Django 6.1.
