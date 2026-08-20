#!/bin/sh
# Entrypoint container backend.
#
# Migrasi dijalankan di sini, bukan di step deploy terpisah, supaya skema DB tak
# pernah tertinggal di belakang kode yang sudah jalan. `set -e` membuat container
# gagal start kalau migrasi gagal — lebih baik daripada aplikasi hidup di atas
# skema yang salah.
set -e

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "[entrypoint] alembic upgrade head..."
  alembic upgrade head
fi

# Worker >1 hanya aman karena backend stateless (AGENTS.md §10 #10). Forecasting
# CPU-bound, jadi jangan lebih dari jumlah core VPS.
WORKERS="${UVICORN_WORKERS:-2}"

echo "[entrypoint] uvicorn: ${WORKERS} worker"
exec uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 8000 \
  --workers "${WORKERS}" \
  --proxy-headers \
  --forwarded-allow-ips '*'
