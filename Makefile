.PHONY: up down test lint fmt

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