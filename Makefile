# Requires Python 3.12 and Node 22. On Windows run these from Git Bash.
PY := backend/.venv/bin/python
ifeq ($(OS),Windows_NT)
PY := backend/.venv/Scripts/python
endif

.PHONY: install dev-api dev-web test lint build docker

install:
	python -m venv backend/.venv && $(PY) -m pip install -r backend/requirements-dev.txt
	cd frontend && npm ci

dev-api:            ## Django on :8000
	cd backend && ../$(PY) manage.py runserver 127.0.0.1:8000

dev-web:            ## Vite on :5173, proxies /api to :8000
	cd frontend && npm run dev

test:
	cd backend && ../$(PY) -m pytest
	cd frontend && npm test

lint:
	cd backend && ../$(PY) -m ruff check . && ../$(PY) -m ruff format --check . && ../$(PY) -m mypy trips/domain
	cd frontend && npm run lint && npm run typecheck

build:
	cd frontend && npm run build

docker:
	docker compose up --build
