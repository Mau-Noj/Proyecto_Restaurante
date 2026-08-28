.PHONY: install migrate makemigrations run test lint services-up services-down

# Activa el virtualenv antes de usar estos comandos:
#   source .venv/bin/activate       (Linux/Mac/Pi)
#   .venv\Scripts\activate          (Windows)

install:
	pip install -r requirements.txt -r requirements-dev.txt

services-up:
	docker compose up -d db redis

services-down:
	docker compose down

migrate:
	python manage.py migrate

makemigrations:
	python manage.py makemigrations

run:
	python manage.py runserver 0.0.0.0:8000

test:
	pytest

lint:
	ruff check .
