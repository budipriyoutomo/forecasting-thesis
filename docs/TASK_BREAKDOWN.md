# Task Breakdown & Roadmap Implementasi
## ForecastIQ — Raw Material & Inventory Forecasting Platform (PPIC)

Setiap fase mengikuti workflow TDD wajib di `AGENTS.md` §3 (Red → Green → Refactor). Jangan mulai fase berikutnya sebelum test fase sebelumnya PASSED dan coverage memenuhi minimum di `AGENTS.md` §3.

---

## Fase 0 — Monorepo Setup ✅
- [x] Inisialisasi repo Git, struktur folder sesuai `ARCHITECTURE.md` §3.
- [x] `AGENTS.md`, `.gitignore`, `.env.example` (backend & frontend).
- [x] Backend: FastAPI skeleton (`/health`, CORS, exception handler), `pyproject.toml`, koneksi Postgres async lazy (`app/db/session.py`), Alembic init (`backend/alembic/`, URL dari `DATABASE_URL`).
- [x] Frontend: Next.js App Router + TypeScript + Tailwind + shadcn/ui + TanStack Query provider, halaman depan cek koneksi backend.
- [x] `docker-compose.yml` untuk dev + `Makefile` (install/dev/test/cov/migrate).
- [x] CI dasar: lint + typecheck + test + coverage gate (`.github/workflows/ci.yml`).

**Selesai jika:** health check endpoint jalan, frontend bisa fetch ke backend, CI hijau di commit kosong.

> Catatan: versi dependency backend dilonggarkan dari pin `==` ke `>=` (lihat komentar di `backend/requirements.txt`) karena pin versi 2024 memaksa build dari source di Python 3.14 (tidak ada wheel prebuilt).

## Fase 1 — Auth (Supabase Auth/JWT) ✅
- [x] Model `users` (id, email, name, role, is_verified) + migration (`alembic/versions/67345c33f31f_*`).
- [x] Integrasi Supabase Auth (`app/services/supabase_auth.py`, GoTrue), endpoint `POST /api/v1/auth/login`, `GET /api/v1/auth/me`. Backend menerbitkan JWT-nya sendiri (pola `app/utils/auth.py`); Supabase dipakai untuk verifikasi kredensial.
- [x] Dependency FastAPI RBAC `require_role(*roles)` (admin/ppic/purchasing/viewer) → 403 `AUTH_FORBIDDEN` (kode baru, lihat `RECONCILIATION.md` #12).
- [x] **TDD**: 401 tanpa token, 401 token expired, happy path login, kredensial salah (401), email belum verified (403), RBAC role check, + unit test authenticator (httpx mock) & repository (session mock).
- [x] Frontend: halaman `/login` (react-hook-form + zod), `useAuth` (login/me/logout), middleware proteksi route grup dashboard (token di cookie), halaman dashboard menampilkan profil.

**Selesai jika:** user bisa login, role membatasi akses sesuai desain, semua test auth PASSED.

> Coverage backend Fase 1: services/endpoint/model auth 100%, total 95%. Frontend: 11 test PASSED (api client + LoginForm), lint + typecheck bersih.

## Fase 2 — Master Data Material ✅
- [x] Model `materials` (code, name, category, unit, lead_time_days, moq, manual_safety_stock) + migration (`6428318b5bb5`).
- [x] CRUD endpoint `api/v1/materials` (GET list/detail, POST, PUT, DELETE) + import via CSV (`POST /materials/import`).
- [x] RBAC: baca semua role terautentikasi; tulis (create/update/delete/import) hanya `admin`.
- [x] **TDD**: happy path CRUD, kode duplikat → 409 `MATERIAL_CODE_EXISTS` (kode baru, `RECONCILIATION.md` #13), 404 material tidak ada, 403 non-admin, import CSV (sukses, kolom wajib hilang, duplikat dalam file, angka tidak valid).
- [x] Frontend: halaman `materials/` — tabel, form tambah/edit (react-hook-form + zod), hook `useMaterials`.

**Selesai jika:** admin bisa kelola master data material penuh dari UI, coverage endpoint ≥ 90%.

> Coverage backend Fase 2: model/repository/service/endpoint material 100%, total 95%. Frontend: 18 test PASSED. Import Excel (.xlsx) ditunda — CSV dulu; menambah Excel = tambah parser di `material_service.import_*` tanpa ubah endpoint.

## Fase 3 — Data Ingestion (Upload & Storage) ✅
- [x] Model `upload_sessions` + `consumption_history` + migration (`9a85016d7be7`). `consumption_history` deviasi: `material_code` + `material_id` nullable (RECONCILIATION #14).
- [x] `storage_service.py`: upload ke R2 `temp/uploads/{session_id}/`, move ke `permanent/datasets/`, client S3 injectable (`build_r2_client`).
- [x] `data_ingestion_service.py`: parsing CSV (pandas), validasi kolom wajib (material_code, date, quantity), deteksi banyak SKU, `extract_consumption_rows` untuk persist.
- [x] Endpoint `POST /uploads` (validasi → temp → permanent → persist session + consumption), `GET /uploads` (riwayat), `GET /uploads/{id}` (detail, 404/403).
- [x] Cron cleanup (`app/jobs/cleanup_temp_uploads.py`, `python -m app.jobs.cleanup_temp_uploads`) — tandai `expired` + hapus temp; tanpa Celery/Redis (MVP sync-first).
- [x] **TDD**: happy path, `UPLOAD_INVALID_FORMAT`, `UPLOAD_FILE_TOO_LARGE`, `INSUFFICIENT_DATA`, `SESSION_EXPIRED` (guard pending kedaluwarsa), 404/403, cleanup, storage (mock S3).
- [x] Frontend: halaman upload (`forecast/new`) + preview + riwayat upload.

**Selesai jika:** upload CSV multi-SKU tervalidasi, tersimpan permanen, dan riwayat upload bisa dilihat.

> Coverage backend Fase 3: upload_service 97%, storage 98%, repos 100%, endpoint 100%, total 95%. Frontend 21 test PASSED. Resolusi `material_id` dari master data; kode belum terdaftar → warning (bukan auto-create material).

## Fase 4 — Auto Model Selection Engine + Manual Override (Core — Prioritas Tertinggi)
- [ ] `types.py`: dataclass `ForecastPoint`, `EngineResult`.
- [ ] `classification.py`: hitung ADI/CV², mapping kuadran Syntetos-Boylan. **TDD dulu** dengan data historis contoh per kuadran (smooth/erratic/intermittent/lumpy).
- [ ] `engines/README.md` (kontrak fungsi untuk engine baru — signature, self-contained backtest+fit+predict+explanation).
- [ ] Implementasi **1 fungsi per metode** (TDD per fungsi, satu test file per metode): `ets_engine.py` (`forecast_ets`), `arima_engine.py` (`forecast_arima`), `lightgbm_engine.py` (`forecast_lightgbm`), **`croston_engine.py`** (`forecast_croston` — wajib untuk kuadran intermittent/lumpy, lihat `RECONCILIATION.md`).
- [ ] `prophet_engine.py`: stub/TODO dulu (dependency berat) — **jangan didaftarkan ke registry** sampai benar diimplementasikan.
- [ ] `registry.py`: `MODEL_REGISTRY` (dict nama→fungsi), `get_enabled_methods()`, `filter_candidates()` per kuadran, baca `FORECAST_ENGINES_ENABLED` dari env.
- [ ] `scoring_engine.py`: MASE + guardrail (bias/tracking signal) + fit kuadran, bobot dari env — dipakai mode auto saja.
- [ ] `forecast_service.py`: orkestrasi dengan 2 cabang — **manual** (skip klasifikasi+scoring, langsung panggil 1 fungsi sesuai `method` yang diminta user, tanpa fallback bila gagal) dan **auto** (klasifikasi → filter kandidat → backtest tiap kandidat → scoring → pilih skor tertinggi).
- [ ] Model `forecast_runs` + `forecast_results` (+ kolom `selection_mode`) + migration.
- [ ] Endpoint trigger forecast run (banyak material sekaligus, field `method` opsional di request body — lihat `ARCHITECTURE.md` §6.8) + polling status.
- [ ] Frontend: `MethodSelector.tsx` (dropdown "Otomatis (Direkomendasikan)" + daftar metode aktif) di halaman `forecast/new/config`, sebelum tombol generate.
- [ ] **TDD menyeluruh** (prioritas tertinggi — ini inti value produk): setiap kuadran punya minimal 1 test dengan data fixture; test mode manual (sukses & `UNSUPPORTED_FORECAST_METHOD`); test `MODEL_SELECTION_FAILED` saat semua kandidat auto gagal; test `INSUFFICIENT_DATA`.

**Selesai jika:** forecast run bisa dijalankan end-to-end untuk banyak material sekaligus (baik mode otomatis maupun manual), setiap kuadran demand (termasuk intermittent/lumpy) menghasilkan forecast (bukan selalu `MODEL_SELECTION_FAILED`), coverage forecasting module ≥ 85%.

> ✅ **Selesai (Fase 4 lengkap).** Model `forecast_runs`+`forecast_results` (+`status` per-material, RECONCILIATION #15) + migration `fae350da01a7`. `forecast_run_service` orkestrasi banyak material: ambil histori dari `consumption_history` → `forecast_service` (satu-satunya entry engine) → persist. Kegagalan 1 material tak menggagalkan run; metode manual tak dikenal ditolak 400 di awal. Endpoint `POST /forecast/runs`, `GET /forecast/runs/{id}` (polling), `GET /forecast/results?material_id=`, `GET /forecast/methods`. Frontend: `MethodSelector` + halaman `forecast/new/config` (pilih material, method, horizon → generate → hasil + explanation). TDD: tiap kuadran (smooth/erratic/intermittent/lumpy) menghasilkan forecast, manual sukses & `UNSUPPORTED_FORECAST_METHOD`, `INSUFFICIENT_DATA` per-material, 404 material, polling. Coverage: forecast layer 100%, engine module ≥85%, total 95%. Frontend 26 test PASSED.

## Fase 5 — Safety Stock & Reorder Point ✅
- [x] Model `reorder_recommendations` + migration (`8e5cdd610f80`).
- [x] `reorder_service.py`: `compute_reorder` (FUNGSI MURNI) — SS = Z·σ·√LT (atau manual override), ROP = μ·LT + SS, order qty = max(MOQ, ceil(S−current)), status urgent/safe/overstock. `SERVICE_LEVEL_Z` dari env (default 1.65 ≈ 95%).
- [x] Endpoint `POST /reorder/recommendations` (generate) + `GET /reorder/recommendations?run_id=&status=` (filter). Lihat RECONCILIATION #16 (POST + `current_stock` sebagai input request).
- [x] **TDD**: lead pendek/panjang, MOQ besar, demand stabil vs volatile, manual SS, batas urgent/safe/overstock — semua angka diverifikasi manual di `test_reorder_compute.py`.
- [x] Frontend: `ReorderTable` (filter status) di halaman `forecast/new/config` + hook `useReorder`.

**Selesai jika:** rekomendasi reorder benar secara matematis dan bisa diverifikasi manual dengan data contoh.

> Coverage backend Fase 5: reorder layer ~100% (service 97%), total 95%. Frontend 31 test PASSED. `current_stock` diterima per-request (default 0), tidak dipersist — skema tak menyimpan stok live.

## Fase 6 — Planner Override & Audit Trail ✅
- [x] Model `overrides` (target_type, target_id, previous_value, new_value, reason NOT NULL) + migration (`6366f084a6d9`).
- [x] `override_service.py`: append-only (baris baru, tidak overwrite), `reason` wajib (`OVERRIDE_REASON_REQUIRED`), snapshot `previous_value` dari target, target polimorfik via resolvers.
- [x] Endpoint `POST /api/v1/overrides`, `GET /api/v1/overrides?target_id=...`. Target tak ada → `OVERRIDE_TARGET_NOT_FOUND` (404, RECONCILIATION #17); target_type invalid → 422 (Literal).
- [x] **TDD**: happy path, reason kosong ditolak, override TIDAK mengubah data asli (assert nilai lama tetap), target 404, audit trail append-only (2 revisi tersimpan).
- [x] Frontend: `OverrideForm` (reason wajib) + `AuditTrail` (sebelum→sesudah, alasan, waktu) + hook `useOverrides`.

**Selesai jika:** planner bisa override forecast/reorder dengan alasan wajib, riwayat lengkap dan tidak pernah menimpa data asli.

> Coverage backend Fase 6: override layer 100%, total 95%. Frontend 35 test PASSED.

## Fase 7 — Dashboard & Visualisasi ✅
- [x] Endpoint `GET /api/v1/dashboard/summary` (`dashboard_service`): jumlah material, run terakhir + MASE rata-rata, distribusi status reorder, jumlah override terbaru.
- [x] Halaman dashboard: stat tiles (material, perlu-reorder, akurasi, override), ringkasan run terakhir, distribusi reorder. `ForecastChart` (recharts) tren forecast + confidence interval band; overlay aktual opsional.
- [x] Komponen `ExplanationBox` — penjelasan bahasa natural per hasil forecast (dipakai di `ForecastResults`).

**Selesai jika:** user non-teknis bisa memahami status forecast, reorder, dan alasan override hanya dari dashboard.

> Coverage backend Fase 7: dashboard layer 100%, total 95%. Frontend 38 test PASSED. ForecastChart di-uji lewat typecheck (render recharts di jsdom di-skip).

## Fase 8 — Export & Laporan ✅
- [x] Export hasil forecast (`GET /forecast/runs/{run_id}/export`) & rekomendasi reorder (`GET /reorder/recommendations/export?format=xlsx`) ke Excel (openpyxl).
- [x] Export laporan reorder ke PDF (`?format=pdf`, fpdf2).
- [x] Simpan hasil export ke `permanent/exports/{user_id}/{run_id}/` (best-effort — kegagalan R2 tidak menggagalkan download).
- [x] Frontend: tombol export (Excel/PDF) di halaman `forecast/new/config`, unduh via blob.

**Selesai jika:** file export terbuka dan datanya sesuai dashboard.

> Coverage backend Fase 8: export layer 100%, total 95%. Frontend 40 test PASSED. Builder (`build_forecast_xlsx`/`build_reorder_xlsx`/`build_reorder_pdf`) fungsi murni (bytes), diverifikasi dengan membuka ulang file (openpyxl load, cek `%PDF`).

## Fase 9 — Hardening, Testing E2E & Deployment
- [ ] Integration test end-to-end: upload → forecast run → reorder → override → dashboard.
- [ ] Review keamanan (rate limiting upload, validasi file, CORS production).
- [ ] Setup deployment: Backend → Railway, Frontend → Vercel, DB/Auth → Supabase, Storage → Cloudflare R2.
- [ ] `JWT_SECRET_KEY` production-grade (256-bit random, secret manager).
- [ ] Sentry / error tracking backend + frontend.
- [ ] Dokumentasi pemakaian untuk end-user (user manual singkat).

**Selesai jika:** aplikasi siap dipakai tim PPIC di lingkungan mendekati production, semua test PASSED, coverage memenuhi minimum di semua layer.

---

## Prioritas Jika Waktu Terbatas (MVP Tercepat)

1. Fase 0 (setup)
2. Fase 2 (master data material, versi sederhana)
3. Fase 3 (upload & ingestion)
4. **Fase 4 (Auto Model Selection Engine — termasuk Croston, jangan dilewati meski buru-buru, karena ini yang membedakan produk ini dari sekadar "moving average calculator")**
5. Fase 5 (reorder point — versi sederhana)
6. Fase 7 (dashboard versi sederhana)

Fase 1 (auth lengkap dengan semua role), Fase 6 (override UI lengkap), Fase 8 (export), dan Fase 9 (hardening penuh) bisa menyusul setelah MVP tervalidasi oleh user PPIC riil.

---
*Lihat `RECONCILIATION.md` untuk konteks kenapa Fase 4 memasukkan Croston/SBA sebagai engine wajib MVP, bukan opsional.*
