FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    # Install into the image's system interpreter so `python manage.py` and
    # `celery` work without activating a venv first.
    UV_PROJECT_ENVIRONMENT=/usr/local

# Match these to your host user (`id -u` / `id -g`) so files the containers
# write into the bind-mounted source tree stay editable from the host.
ARG UID=1000
ARG GID=1000

RUN groupadd --gid "$GID" app \
    && useradd --uid "$UID" --gid "$GID" --create-home --shell /bin/bash app

WORKDIR /app

# Dependencies are their own layer, so editing project code doesn't reinstall them.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-install-project

# Named volumes inherit ownership from the image path they mount over, so
# creating these up front keeps beat and flower writable as a non-root user.
RUN mkdir -p /var/lib/celery /data && chown -R app:app /var/lib/celery /data /app

COPY --chown=app:app . .

# Celery's worker refuses to run as root without C_FORCE_ROOT, and non-root is
# what you want in production anyway.
USER app

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
