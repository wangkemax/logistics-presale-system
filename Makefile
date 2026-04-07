.PHONY: dev up down logs test migrate

# Start all services
up:
	docker compose up -d

# Stop all services
down:
	docker compose down

# View logs
logs:
	docker compose logs -f

# Backend logs only
logs-backend:
	docker compose logs -f backend

# Run backend locally (without Docker)
dev-backend:
	cd backend && uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Run frontend locally (without Docker)
dev-frontend:
	cd frontend && npm run dev

# Run both locally
dev:
	make dev-backend & make dev-frontend

# Database migration
migrate:
	cd backend && alembic upgrade head

# Create new migration
migrate-new:
	cd backend && alembic revision --autogenerate -m "$(msg)"

# Install backend deps
install-backend:
	cd backend && pip install -r requirements.txt

# Install frontend deps
install-frontend:
	cd frontend && npm install

# Install all
install: install-backend install-frontend

# Reset database
reset-db:
	docker compose exec db psql -U postgres -c "DROP DATABASE IF EXISTS logistics_presale;"
	docker compose exec db psql -U postgres -c "CREATE DATABASE logistics_presale;"
	docker compose restart backend

# E2E tests
test:
	cd backend && python -m pytest tests/test_unit.py -v

test-e2e:
	cd backend && python tests/test_e2e.py

# Integration tests (20 steps)
test-integration:
	cd backend && python tests/test_integration.py

# Seed knowledge base
seed:
	cd backend && python -m app.scripts.seed_knowledge
