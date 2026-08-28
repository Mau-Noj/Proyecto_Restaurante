# Zennin Bistro — Sistema de gestión de restaurante

Django + PostgreSQL + Redis (Channels/Daphne para tiempo real en KDS).

## Desarrollo local

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
make install                       # o: pip install -r requirements.txt -r requirements-dev.txt

cp .env.example .env                # ajusta si hace falta
make services-up                   # levanta Postgres + Redis (docker compose)
make migrate
make run                           # http://localhost:8000
```

## Tests y lint

Comando estandarizado para correr la suite completa (el mismo que usa `ci.yml`):

```bash
make services-up   # Postgres + Redis deben estar corriendo
make test          # equivalente a: pytest
make lint          # equivalente a: ruff check .
```

Ver `Makefile` para el resto de atajos (`make migrate`, `make makemigrations`, `make run`).

## Más documentación

- [`CONTRIBUTING.md`](CONTRIBUTING.md) — flujo de ramas (Git Flow), convenciones de PR, CI/CD.
- [`infra/README.md`](infra/README.md) — despliegue (Terraform + Ansible).
