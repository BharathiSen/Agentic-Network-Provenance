.PHONY: up down test lint fmt schema

up:
	docker compose up -d

down:
	docker compose down

test:
	uv run pytest

lint:
	uv run ruff check .

fmt:
	uv run black .

schema:
	uv run python scripts/export_schema.py
