# ForecastIQ — Makefile
# Monorepo: frontend (Next.js) + backend (FastAPI).

# Path virtualenv backend (dibuat oleh `make venv`; .venv/ sudah ada di .gitignore)
VENV := backend/.venv/bin
PY   := $(abspath $(VENV))/python
PIP  := $(abspath $(VENV))/pip

.PHONY: dev backend frontend install venv install-backend install-frontend \
        test test-backend test-frontend cov lint typecheck \
        migrate revision seed-users up down logs clean help

# Default: jalanin frontend + backend bareng
dev:
	@echo "🚀 Menjalankan frontend + backend..."
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) backend & \
	$(MAKE) frontend & \
	wait

# Backend saja (FastAPI / uvicorn)
backend:
	@echo "🔧 Backend → http://localhost:8000 (docs: /docs)"
	cd backend && $(abspath $(VENV))/uvicorn app.main:app --reload

# Frontend saja (Next.js)
frontend:
	@echo "🎨 Frontend → http://localhost:3000"
	cd frontend && npm run dev

# --- Setup -------------------------------------------------------------------

# Bikin virtualenv backend kalau belum ada
venv:
	@test -d backend/.venv || (echo "🐍 Membuat backend/.venv..." && python3 -m venv backend/.venv)

install-backend: venv
	@echo "📦 Install dependencies backend..."
	$(PIP) install --upgrade pip
	$(PIP) install -r backend/requirements.txt

install-frontend:
	@echo "📦 Install dependencies frontend..."
	cd frontend && npm install

# Install dependencies frontend + backend
install: install-backend install-frontend

# --- Test & Quality Gate -----------------------------------------------------

# Test backend (pytest) — TDD wajib, lihat AGENTS.md §3
test-backend:
	@echo "🧪 Backend tests..."
	cd backend && $(PY) -m pytest -q

# Test frontend (vitest)
test-frontend:
	@echo "🧪 Frontend tests..."
	cd frontend && npm test

test: test-backend test-frontend

# Coverage backend + baris yang belum tertutup.
# Minimum per layer ada di AGENTS.md §3 (routes 90%, services 85%, engine 85%, storage 80%, models 70%).
cov:
	@echo "📊 Coverage backend..."
	cd backend && $(PY) -m pytest --cov=app --cov-report=term-missing -q

lint:
	@echo "🔍 Lint frontend..."
	cd frontend && npx eslint src

typecheck:
	@echo "🔍 Typecheck frontend..."
	cd frontend && npx tsc --noEmit

# --- Database (Fase 1+) ------------------------------------------------------

# Migrasi database ke versi terbaru
migrate:
	@echo "🧬 Alembic upgrade head..."
	cd backend && $(abspath $(VENV))/alembic upgrade head

# User demo per role untuk development (butuh migrate dulu). Idempoten.
seed-users:
	@echo "👤 Seed user demo (development)..."
	cd backend && $(PY) -m app.scripts.seed_dev_users

# Bikin revisi baru: make revision m="tambah tabel forecast_results"
revision:
	@test -n "$(m)" || (echo "❌ Pakai: make revision m=\"pesan migrasi\"" && exit 1)
	cd backend && $(abspath $(VENV))/alembic revision --autogenerate -m "$(m)"

# --- Docker ------------------------------------------------------------------

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

# --- Housekeeping ------------------------------------------------------------

clean:
	@echo "🧹 Bersihin cache..."
	find backend -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.coverage backend/htmlcov frontend/.next

help:
	@echo "make dev        → jalankan frontend + backend sekaligus"
	@echo "make frontend   → jalankan frontend saja (:3000)"
	@echo "make backend    → jalankan backend saja (:8000)"
	@echo "make install    → bikin venv + install dependencies frontend & backend"
	@echo "make test       → test backend (pytest) + frontend (vitest)"
	@echo "make cov        → coverage backend (gate: AGENTS.md §3)"
	@echo "make lint       → eslint frontend"
	@echo "make typecheck  → tsc --noEmit frontend"
	@echo "make migrate    → alembic upgrade head"
	@echo "make revision   → alembic revision --autogenerate m=\"pesan\""
	@echo "make seed-users → user demo per role untuk development"
	@echo "make up/down    → docker compose up -d / down"
	@echo "make clean      → hapus cache pytest/next/__pycache__"
