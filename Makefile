.PHONY: help dev down logs build test backend-test backend-shell frontend-dev fmt check prod prod-logs deploy-helm

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
	@echo "make check          - everything CI runs (lint, tests, typecheck, build)"
	@echo "make prod           - run the public stack (compose + cloudflare tunnel)"
	@echo "make prod-logs      - tail production backend logs"
	@echo "make deploy-helm    - helm upgrade --install (multi-node only, not v1)"

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

check:
	cd backend && . .venv/bin/activate && ruff check . && pytest -q
	cd frontend && npx tsc --noEmit && BACKEND_URL=http://localhost:9999 npm run build

# Public deploy. Reads PUBLIC_HOSTNAME and CLOUDFLARE_TUNNEL_TOKEN from .env;
# the backend refuses to start if the config is unsafe. See docs/DEPLOYMENT.md.
prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

prod-logs:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f backend

# Multi-node only. v1 runs on Compose — see docs/SPEC.md §1.2.
deploy-helm:
	helm upgrade --install agentdojo deploy/helm -f deploy/helm/values.prod.yaml
