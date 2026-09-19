.PHONY: up down test lint seed

up:
	docker compose up --build

down:
	docker compose down

test:
	cd backend && pytest
	cd frontend && npm run test

lint:
	cd backend && ruff check app tests
	cd frontend && npm run lint && npm run typecheck

seed:
	python scripts/build_seed.py

