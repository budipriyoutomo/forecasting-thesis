# ForecastIQ — Makefile
# Monorepo: frontend (Next.js) + backend (FastAPI).

# Path virtualenv backend (dibuat oleh `make venv`; .venv/ sudah ada di .gitignore)
VENV := backend/.venv/bin
PY   := $(abspath $(VENV))/python
PIP  := $(abspath $(VENV))/pip

.PHONY: dev backend frontend install venv install-backend install-frontend \
        test test-backend test-frontend cov lint typecheck \
        migrate revision seed-users seed-demo up down logs clean help \
        prod-check prod-up prod-down prod-restart prod-ps prod-logs prod-deploy \
        prod-migrate prod-downgrade prod-psql prod-shell prod-backup prod-restore \
        prod-cleanup

# Guard: mesin production ditandai keberadaan .env.prod. Target dev di bawah
# memakai docker-compose.yml (bind mount, uvicorn --reload, npm run dev, Postgres
# terbuka di :5432) atau backend/.venv yang tidak ada di server — dijalankan di VPS
# hampir selalu bukan yang dimaksud, dan untuk `up` berbahaya. Timpa dengan
# FORCE_DEV=1 kalau memang disengaja.
define guard-dev
@test ! -f .env.prod || test -n "$(FORCE_DEV)" || ( \
	echo "❌ Ada .env.prod → ini kelihatannya mesin production."; \
	echo "   Target '$@' adalah target DEVELOPMENT, bukan production."; \
	echo "   Yang kamu cari: make prod-up | prod-deploy | prod-migrate | prod-logs (lihat make help)"; \
	echo "   Kalau memang disengaja: FORCE_DEV=1 make $@"; \
	exit 1)
endef

# Default: jalanin frontend + backend bareng
dev:
	$(guard-dev)
	@echo "🚀 Menjalankan frontend + backend..."
	@trap 'kill 0' INT TERM EXIT; \
	$(MAKE) backend & \
	$(MAKE) frontend & \
	wait

# Backend saja (FastAPI / uvicorn)
backend:
	$(guard-dev)
	@echo "🔧 Backend → http://localhost:8000 (docs: /docs)"
	cd backend && $(abspath $(VENV))/uvicorn app.main:app --reload

# Frontend saja (Next.js)
frontend:
	$(guard-dev)
	@echo "🎨 Frontend → http://localhost:3000"
	cd frontend && npm run dev

# --- Setup -------------------------------------------------------------------

# Bikin virtualenv backend kalau belum ada
venv:
	@test -d backend/.venv || (echo "🐍 Membuat backend/.venv..." && python3 -m venv backend/.venv)

install-backend: venv
	$(guard-dev)
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
	$(guard-dev)
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
	$(guard-dev)
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
	$(guard-dev)
	@echo "🧬 Alembic upgrade head..."
	cd backend && $(abspath $(VENV))/alembic upgrade head

# User demo per role untuk development (butuh migrate dulu). Idempoten.
seed-users:
	$(guard-dev)
	@echo "👤 Seed user demo (development)..."
	cd backend && $(PY) -m app.scripts.seed_dev_users

# Data demo (produk, material, BOM, histori 36 bulan, gudang). Butuh seed-users dulu. Idempoten.
seed-demo:
	$(guard-dev)
	@echo "🌱 Seed data demo (development)..."
	cd backend && $(PY) -m app.scripts.seed_demo_data

# Bikin revisi baru: make revision m="tambah tabel forecast_results"
revision:
	$(guard-dev)
	@test -n "$(m)" || (echo "❌ Pakai: make revision m=\"pesan migrasi\"" && exit 1)
	cd backend && $(abspath $(VENV))/alembic revision --autogenerate -m "$(m)"

# --- Docker (dev) ------------------------------------------------------------

up:
	$(guard-dev)
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

# --- Docker (production / VPS) -----------------------------------------------
# Konfigurasi ada di .env.prod (salin dari .env.prod.example, JANGAN di-commit).
# Semua target di bawah ini yang dipakai sehari-hari di server.
PROD := docker compose --env-file .env.prod -f docker-compose.prod.yml

# Direktori backup DB (di luar repo supaya tidak ikut ter-commit / terhapus `clean`).
BACKUP_DIR ?= $(HOME)/forecastiq-backups

# Validasi konfigurasi SEBELUM build — lebih baik gagal di sini daripada 10 menit
# kemudian saat container start dengan pesan yang tidak jelas.
prod-check:
	@test -f .env.prod || (echo "❌ .env.prod belum ada. Jalankan: cp .env.prod.example .env.prod && chmod 600 .env.prod" && exit 1)
	@grep -q '^JWT_SECRET_KEY=.\{16,\}' .env.prod || (echo "❌ JWT_SECRET_KEY kosong/terlalu pendek. Bikin: openssl rand -hex 32" && exit 1)
	@grep -q '^POSTGRES_PASSWORD=.\{8,\}' .env.prod || (echo "❌ POSTGRES_PASSWORD kosong/terlalu pendek. Bikin: openssl rand -base64 24" && exit 1)
	@! grep -q 'GANTI_PASSWORD' .env.prod || (echo "❌ DATABASE_URL masih berisi GANTI_PASSWORD — samakan dengan POSTGRES_PASSWORD." && exit 1)
	@! grep -q '^DOMAIN=.*example\.com' .env.prod || (echo "❌ DOMAIN masih forecastiq.example.com — isi domain sungguhan." && exit 1)
	@grep -q '^SUPABASE_URL=..*' .env.prod || echo "⚠️  SUPABASE_URL kosong → tidak akan ada yang bisa login (lihat DEPLOYMENT.md §1.2)"
	@grep -q '^S3_ACCESS_KEY=..*' .env.prod || echo "⚠️  S3_ACCESS_KEY kosong → upload & export akan gagal (DEPLOYMENT.md §1.3)"
	@grep -qE '^(DEFAULT_ORDERING_COST|DEFAULT_HOLDING_COST_RATE)=[0.]*$$' .env.prod && echo "⚠️  Biaya pesan/simpan masih 0 → EOQ & cost summary akan tampil 0 (DEPLOYMENT.md §3.2)" || true
	@$(PROD) config >/dev/null && echo "✅ .env.prod & compose production valid"

# Build + start. Migrasi alembic jalan otomatis di entrypoint backend.
prod-up: prod-check
	$(PROD) up -d --build

prod-down:
	$(PROD) down

prod-restart:
	$(PROD) restart $(s)

prod-ps:
	@$(PROD) ps

# Semua service, atau satu saja: make prod-logs s=backend
prod-logs:
	$(PROD) logs -f $(s)

# Deploy ulang setelah git pull. `--build` wajib kalau NEXT_PUBLIC_* berubah:
# nilainya di-inline ke bundel frontend saat build, bukan dibaca saat runtime.
prod-deploy: prod-check
	$(PROD) up -d --build
	@$(PROD) ps

# --- Production: database ----------------------------------------------------
# Migrasi normalnya jalan otomatis saat backend start. Target ini untuk kasus
# manual (RUN_MIGRATIONS=false, atau rollback).

prod-migrate:
	$(PROD) exec -T backend alembic upgrade head

# Mundur n revisi (default 1): make prod-downgrade n=2
# Migrasi TIDAK ikut mundur otomatis saat rollback kode — lihat DEPLOYMENT.md §7.4.
prod-downgrade:
	$(PROD) exec -T backend alembic downgrade -$(or $(n),1)

# psql interaktif ke DB production.
prod-psql:
	$(PROD) exec postgres sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

# Shell di dalam container backend.
prod-shell:
	$(PROD) exec backend sh

# Backup DB terkompresi ke $(BACKUP_DIR). Salin keluar dari VPS secara berkala —
# backup yang hanya ada di mesin yang sama tidak menolong saat VPS-nya yang hilang.
prod-backup:
	@mkdir -p $(BACKUP_DIR)
	@$(PROD) exec -T postgres sh -c 'pg_dump -U "$$POSTGRES_USER" "$$POSTGRES_DB"' \
		| gzip > $(BACKUP_DIR)/db-$$(date +%F-%H%M).sql.gz
	@ls -lh $(BACKUP_DIR) | tail -3

# Restore dari file backup: make prod-restore f=~/forecastiq-backups/db-2026-08-20-0200.sql.gz
prod-restore:
	@test -n "$(f)" || (echo "❌ Pakai: make prod-restore f=path/ke/backup.sql.gz" && exit 1)
	@test -f "$(f)" || (echo "❌ File tidak ada: $(f)" && exit 1)
	@echo "⚠️  Ini menimpa isi database production dengan $(f)."
	@printf "   Ketik 'ya' untuk lanjut: " && read jawab && test "$$jawab" = "ya" || (echo "Dibatalkan." && exit 1)
	gunzip -c "$(f)" | $(PROD) exec -T postgres sh -c 'psql -U "$$POSTGRES_USER" -d "$$POSTGRES_DB"'

# Cron pembersih file temp di object storage — jadwalkan tiap 30 menit di crontab VPS.
# Pakai path absolut ke docker/make: PATH cron minim (lihat DEPLOYMENT.md §7.1).
#   */30 * * * * cd /path/ke/forecastiq && /usr/bin/make prod-cleanup >> /var/log/forecastiq-cleanup.log 2>&1
prod-cleanup:
	$(PROD) exec -T backend python -m app.jobs.cleanup_temp_uploads

# --- Housekeeping ------------------------------------------------------------

clean:
	@echo "🧹 Bersihin cache..."
	find backend -type d -name __pycache__ -prune -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/.pytest_cache backend/.coverage backend/htmlcov frontend/.next

help:
	@echo "— Development —"
	@echo "make dev         → jalankan frontend + backend sekaligus"
	@echo "make frontend    → jalankan frontend saja (:3000)"
	@echo "make backend     → jalankan backend saja (:8000)"
	@echo "make install     → bikin venv + install dependencies frontend & backend"
	@echo "make test        → test backend (pytest) + frontend (vitest)"
	@echo "make cov         → coverage backend (gate: AGENTS.md §3)"
	@echo "make lint        → eslint frontend"
	@echo "make typecheck   → tsc --noEmit frontend"
	@echo "make migrate     → alembic upgrade head (lokal)"
	@echo "make revision    → alembic revision --autogenerate m=\"pesan\""
	@echo "make seed-users  → user demo per role untuk development"
	@echo "make seed-demo   → data demo: produk, material, BOM, histori 36 bulan, gudang"
	@echo "make up/down     → docker compose up -d / down (dev)"
	@echo "make clean       → hapus cache pytest/next/__pycache__"
	@echo ""
	@echo "— Production / VPS (butuh .env.prod) — runbook: docs/DEPLOYMENT.md —"
	@echo "make prod-check     → validasi .env.prod & compose sebelum build"
	@echo "make prod-up        → build + start stack production"
	@echo "make prod-deploy    → deploy ulang setelah git pull (build ulang)"
	@echo "make prod-down      → hentikan stack (data & volume tetap aman)"
	@echo "make prod-restart   → restart semua, atau satu: s=backend"
	@echo "make prod-ps        → status container"
	@echo "make prod-logs      → ikuti log; satu service: s=backend"
	@echo "make prod-migrate   → alembic upgrade head di container"
	@echo "make prod-downgrade → mundur n revisi (default 1): n=2"
	@echo "make prod-psql      → psql interaktif ke DB production"
	@echo "make prod-shell     → shell di container backend"
	@echo "make prod-backup    → dump DB terkompresi ke $(BACKUP_DIR)"
	@echo "make prod-restore   → restore dari backup: f=path/ke/backup.sql.gz"
	@echo "make prod-cleanup   → pembersih file temp (jadwalkan di cron)"
	@echo ""
	@echo "Target development di mesin ber-.env.prod ditolak; timpa dengan FORCE_DEV=1."
