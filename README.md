# ForecastIQ

AI-powered raw material & inventory forecasting platform untuk PPIC (Production Planning & Inventory Control).

## Mulai di sini

1. Baca **`AGENTS.md`** — instruksi wajib untuk siapapun (manusia atau AI coding assistant) yang mengerjakan repo ini.
2. Baca `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/TASK_BREAKDOWN.md` (dalam urutan itu).
3. Kalau ada pertanyaan "kenapa keputusan X bukan Y", cek `docs/RECONCILIATION.md` dulu sebelum bertanya ulang.

## Menjalankan (cara cepat, dari root repo)

```bash
make install     # venv backend + npm install frontend
make dev         # backend :8000 + frontend :3000 sekaligus
make test        # pytest + vitest
make cov         # coverage backend (gate: AGENTS.md §3)
```

Salin dulu file env-nya: `cp backend/.env.example backend/.env` dan
`cp frontend/.env.local.example frontend/.env.local`.

Cek koneksi: buka http://localhost:3000 — halaman depan menampilkan status
"Backend terhubung" hasil pemanggilan `GET /health` (kriteria selesai Fase 0).

### Manual (tanpa make)

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && uvicorn app.main:app --reload

cd frontend && npm install && npm run dev
```

### macOS: OpenMP untuk LightGBM

`lightgbm` (Fase 4) butuh runtime OpenMP native. Di macOS:

```bash
brew install libomp
```

Kalau `brew install libomp` lama (build dari source di beberapa setup), alternatif
cepat: pakai `libomp.dylib` yang sudah dibundel `scikit-learn` di venv —

```bash
install_name_tool -add_rpath \
  "$(cd backend/.venv/lib/python*/site-packages/sklearn/.dylibs && pwd)" \
  backend/.venv/lib/python*/site-packages/lightgbm/lib/lib_lightgbm.dylib
```

Di Linux (termasuk CI) tidak perlu langkah ini — wheel LightGBM sudah membawa OpenMP.

### Database

Migrasi memakai Alembic (`backend/alembic/`), URL dibaca dari `DATABASE_URL`
di `backend/.env` — bukan dari `alembic.ini`, supaya secret tidak ikut commit.

```bash
make migrate                          # alembic upgrade head
make revision m="tambah tabel users"  # bikin migrasi baru
```

## Status implementasi

Lihat `docs/TASK_BREAKDOWN.md` untuk daftar fase lengkap. Saat ini:

- **Fase 0** (setup) selesai: monorepo + Makefile, FastAPI skeleton (`/health`, CORS, session DB async lazy), Alembic siap pakai, Next.js App Router + Tailwind + shadcn/ui + TanStack Query, dan CI GitHub Actions (lint + typecheck + test + coverage gate).
- **Fase 1** (auth) selesai: tabel `users` + migration, login via Supabase Auth (`POST /api/v1/auth/login`, `GET /api/v1/auth/me`) dengan JWT backend, RBAC `require_role` (admin/ppic/purchasing/viewer), frontend halaman `/login` + middleware proteksi route. Coverage backend 95%.
- **Fase 2** (master data material) selesai: tabel `materials` + migration, CRUD `api/v1/materials` + import CSV (admin-only untuk tulis), frontend halaman `materials/` (tabel + form tambah/edit). Coverage backend 95%.
- **Fase 3** (data ingestion) selesai: tabel `upload_sessions` + `consumption_history` + migration, `storage_service` (R2 temp→permanent), `upload_service` (validasi + persist + resolusi material), endpoint `POST/GET /uploads`, cron cleanup temp (`python -m app.jobs.cleanup_temp_uploads`), frontend halaman upload + preview + riwayat. Coverage backend 95%.
- **Fase 4** (Auto Model Selection Engine + Manual Override — core) selesai: tabel `forecast_runs` + `forecast_results` + migration, `forecast_run_service` (run banyak material, ambil data dari `consumption_history`, persist hasil, kegagalan per-material tak menggagalkan run), endpoint `POST /forecast/runs` + polling + `GET /forecast/methods`, frontend `MethodSelector` + halaman `forecast/new/config`. Tiap kuadran demand menghasilkan forecast; mode manual tanpa fallback. Coverage backend 95% (forecast layer 100%).
- **Fase 5** (safety stock & reorder point) selesai: tabel `reorder_recommendations` + migration, `reorder_service.compute_reorder` (fungsi murni: SS/ROP/order qty + status urgent/safe/overstock, MOQ & manual SS diperhitungkan), endpoint `POST/GET /reorder/recommendations` (filter status), frontend `ReorderTable`. Angka diverifikasi manual di test. Coverage backend 95%.
- **Fase 6** (planner override & audit trail) selesai: tabel `overrides` (append-only) + migration, `override_service` (reason wajib, snapshot previous_value, tidak pernah menimpa data asli), endpoint `POST/GET /overrides`, frontend `OverrideForm` + `AuditTrail`. Coverage backend 95%.
- **Fase 4 inti** (Auto Model Selection Engine + Manual Override) sudah berjalan sebagai *service layer* (`app/services/forecasting/`), dengan 4 metode forecasting terimplementasi penuh — masing-masing **1 fungsi per metode** (`ets_engine.py`, `arima_engine.py`, `croston_engine.py`, `lightgbm_engine.py`) — plus endpoint `POST /api/v1/forecast/runs` yang mendukung mode **otomatis** (`method: null`) maupun **manual** (`method: "arima"`, dst — lihat `docs/ARCHITECTURE.md` §6.8).
- `prophet_engine.py` sengaja **belum** diimplementasikan (dependency berat) — lihat docstring di file tsb.
- Endpoint di atas belum tersambung ke database/R2 sungguhan (masih menerima data historis langsung di body request) — itu bagian **Fase 1–3** (auth, master data, upload persisten) yang belum dikerjakan.
- Belum ada: reorder/safety stock (Fase 5), planner override & audit trail (Fase 6), dashboard (Fase 7), export (Fase 8).
