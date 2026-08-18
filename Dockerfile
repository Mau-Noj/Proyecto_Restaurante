# syntax=docker/dockerfile:1
FROM python:3.12-slim AS builder
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install -r requirements.txt

FROM python:3.12-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    DJANGO_SETTINGS_MODULE=config.settings

RUN groupadd -r app && useradd -r -g app -d /app app
WORKDIR /app
COPY --from=builder /opt/venv /opt/venv
COPY . .

# Valores dummy solo para que settings.py cargue durante el build (collectstatic
# no abre conexión real a DB/Redis). En runtime, docker-compose.yml.j2 los
# sobreescribe con el .env real generado por Ansible.
ENV DEBUG=False SECRET_KEY=build-time-key-unused-at-runtime \
    ALLOWED_HOSTS=localhost \
    DATABASE_URL=postgres://user:pass@localhost:5432/db \
    REDIS_URL=redis://localhost:6379/0
RUN python manage.py collectstatic --noinput

RUN chown -R app:app /app
USER app
EXPOSE 8000
CMD ["daphne", "-b", "0.0.0.0", "-p", "8000", "config.asgi:application"]
