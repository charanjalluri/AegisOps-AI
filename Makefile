# ==============================================================================
# AegisOps AI - Developer Makefile
# ==============================================================================

.PHONY: help setup up down clean logs test test-unit test-integration reset-demo ps

PYTHON := python
VENV_PYTHON := .venv/bin/python
ifeq ($(OS),Windows_NT)
	VENV_PYTHON := .venv\Scripts\python.exe
endif

help:
	@echo "AegisOps AI Automation Commands:"
	@echo "  make setup            - Initialize .env from .env.example"
	@echo "  make up               - Start local Docker Compose infrastructure"
	@echo "  make down             - Stop local Docker Compose infrastructure"
	@echo "  make clean            - Stop containers and REMOVE persistent volumes"
	@echo "  make logs             - Tail container logs"
	@echo "  make ps               - Show container status"
	@echo "  make test-unit        - Run offline unit tests"
	@echo "  make test-integration - Run live Docker integration tests"
	@echo "  make test             - Run unit tests"
	@echo "  make reset-demo       - Reset demo tables without destroying containers"

setup:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; else echo ".env already exists"; fi

up:
	docker compose up -d

down:
	docker compose down

clean:
	docker compose down -v --remove-orphans

logs:
	docker compose logs -f

ps:
	docker compose ps

test-unit:
	pytest tests/unit -v

test-integration:
	pytest tests/integration -v

test: test-unit

reset-demo:
	$(PYTHON) scripts/reset-demo.py
