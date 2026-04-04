.PHONY: help build up down restart logs shell db-shell migrate migrate-auto migrate-upgrade migrate-downgrade clean test

help:
	@echo "FinanzApp - Makefile Commands"
	@echo "=============================="
	@echo "build          - Build Docker containers"
	@echo "up             - Start all services"
	@echo "down           - Stop all services"
	@echo "restart        - Restart all services"
	@echo "logs           - View logs"
	@echo "shell          - Access API container shell"
	@echo "db-shell       - Access PostgreSQL shell"
	@echo "migrate        - Create new migration"
	@echo "migrate-auto   - Auto-generate migration"
	@echo "migrate-upgrade - Apply migrations"
	@echo "migrate-downgrade - Rollback one migration"
	@echo "clean          - Remove containers and volumes"
	@echo "test           - Run tests"

build:
	docker-compose build

up:
	docker-compose up -d

down:
	docker-compose down

restart:
	docker-compose restart

logs:
	docker-compose logs -f

shell:
	docker-compose exec api /bin/bash

db-shell:
	docker-compose exec postgres psql -U postgres -d finanzapp

migrate:
	docker-compose exec api alembic revision -m "$(message)"

migrate-auto:
	docker-compose exec api alembic revision --autogenerate -m "$(message)"

migrate-upgrade:
	docker-compose exec api alembic upgrade head

migrate-downgrade:
	docker-compose exec api alembic downgrade -1

clean:
	docker-compose down -v
	rm -rf postgres_data/

test:
	docker-compose exec api pytest
