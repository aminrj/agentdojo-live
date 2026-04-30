.PHONY: help dev down logs build test backend-test backend-shell frontend-dev fmt deploy

help:
	@echo "make dev            - run full stack locally (docker compose)"
	@echo "make down           - stop the stack"
	@echo "make logs           - tail backend + frontend logs"
	@echo "make build          - build all docker images"
	@echo "make test           - run backend tests"
	@echo "make backend-test   - run pytest in backend venv"
	@echo "make backend-shell  - drop into backend python repl"
	@echo "make frontend-dev   - run frontend dev server (npm run dev)"
	@echo "make fmt            - run ruff/format on the backend"
	@echo "make deploy         - helm upgrade --install (prod values)"

dev:
	@test -f .env || cp .env.example .env
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f backend frontend

build:
	docker compose build

test: backend-test

backend-test:
	cd backend && . .venv/bin/activate && pytest -q

backend-shell:
	cd backend && . .venv/bin/activate && python

frontend-dev:
	cd frontend && npm run dev

fmt:
	cd backend && . .venv/bin/activate && ruff check --fix . && ruff format .

deploy:
	helm upgrade --install agentdojo deploy/helm -f deploy/helm/values.prod.yaml
