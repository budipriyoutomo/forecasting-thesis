---
description: Pre-push gate — cek backward-compatibility & aturan wajib AGENTS.md, lalu sinkronkan dokumen konteks. Jalankan sebelum commit/push manual. TIDAK commit.
---

Jalankan pemeriksaan pra-push lalu sinkronkan dokumentasi. **JANGAN commit/push** — user yang melakukannya setelah review.

**HEMAT TOKEN:** lihat diff dulu, jalankan HANYA cek yang relevan dengan area yang berubah, jangan eksplor file yang tak tersentuh.

## 1. Lihat scope perubahan
- `git status` dan `git diff --stat` (staged + unstaged) → tentukan apakah backend, frontend, atau dokumen yang berubah. Selebihnya menyesuaikan ini.

## 2. Cek aturan wajib ForecastIQ (sesuaikan area yang berubah)

Rujukan: `AGENTS.md` §3 (TDD), §4 (API standard), §5 (model selection + override), §10 (larangan).

- **Backend berubah:** `make test-backend`. Kalau menyentuh service/engine/route → `make cov` dan bandingkan dengan gate di `AGENTS.md` §3 (routes 90%, services 85%, forecasting engine 85%, storage 80%, models 70%).
- **Format response:** `grep -rn "JSONResponse\|return {" backend/app/api` → tiap response wajib bentuk `{"success": ..., "data"/"error": ...}` (§4).
- **Error code:** `grep -rn "code=\|\"code\":" backend/app` → semua code harus ada di daftar `AGENTS.md` §4. Code baru yang belum terdaftar = blocker (harus ditambahkan dulu ke `AGENTS.md` + `docs/ARCHITECTURE.md` §5).
- **Tidak ada logic forecasting inline di router:** `grep -rn "forecast_ets\|forecast_arima\|forecast_lightgbm\|forecast_croston\|MODEL_REGISTRY" backend/app/api` → harus kosong. Semua lewat `forecast_service.py` (§10 no.2).
- **Tidak ada hardcode engine/bobot:** `grep -rn "0\.6\|0\.3\|\[.ets., .arima.\|\"ets\"" backend/app/services/forecasting` → daftar engine & bobot harus dari settings/env (`FORECAST_ENGINES_ENABLED`, `SCORING_WEIGHT_*`), bukan literal di kode (§10 no.1).
- **Engine baru:** pastikan berbentuk **fungsi murni** `def forecast_<method>(df, horizon) -> EngineResult` (bukan class/Protocol), sudah terdaftar di `registry.py`, punya test sendiri `tests/unit/test_<method>_engine.py`, dan kuadran `intermittent`/`lumpy` tetap punya kandidat `croston` (§5, §10 no.12 & 15).
- **Env var baru:** kalau `app/config.py` berubah, pastikan `backend/.env.example` **dan** daftar env di `AGENTS.md` §5 ikut diupdate.
- **Frontend berubah:** `make typecheck` + `npx eslint <file yang berubah>`. Untuk perubahan besar/berisiko, `cd frontend && npm run build`.
- **Dependency baru:** `package.json` berubah → lockfile (`package-lock.json`) harus ikut berubah. `requirements.txt` berubah → versi harus dipin (`==`).
- **Migrasi DB:** ada revisi Alembic baru → cek hanya ada satu `head` (`cd backend && .venv/bin/alembic heads`) dan `downgrade` terisi, bukan `pass`.
- **Secret:** `git diff | grep -in "SUPABASE_SERVICE_ROLE\|R2_SECRET\|JWT_SECRET_KEY=\|sk-"` → pastikan tidak ada nilai asli ter-stage, dan `.env` tidak ikut ter-commit (§10 no.6).
- **Risiko data (bukan kode):** kalau schema `forecast_results`/`overrides` berubah, ingatkan bahwa data historis & override lama bersifat append-only — migrasi tidak boleh overwrite/menghapus jejak (§6).

## 3. Sinkronkan dokumen konteks
Dari diff, identifikasi perubahan yang MENGUBAH konteks terdokumentasi: endpoint/field/kolom baru, error code baru, engine baru, mekanisme scoring, konvensi, keputusan arsitektur. Update **HANYA** yang out-of-sync, **edit bedah (jangan tulis ulang)**:
- `backend/app/services/forecasting/engines/README.md` — kontrak fungsi engine, minimum data, kuadran yang didukung.
- `docs/ARCHITECTURE.md` — data model (§4), API contract (§5), forecasting engine (§6), storage flow (§7), error handling (§8).
- `AGENTS.md` — konvensi/instruksi proyek tingkat tinggi (termasuk daftar error code & env var).
- `docs/RECONCILIATION.md` — WAJIB kalau ada keputusan arsitektur yang berubah dari yang tertulis di `AGENTS.md` (§10 no.13).
- Memory (`MEMORY.md` + file memory) — fakta durable lintas-sesi.

> Sinkronisasi `docs/PRD.md` + `docs/ARCHITECTURE.md` yang lebih dalam ada di `/update-docs` — di sini cukup yang jelas-jelas out-of-sync dengan diff.

## 4. Laporkan (jangan commit)
- Ringkasan hasil cek: lulus/gagal + apa yang gagal & kenapa.
- Coverage aktual vs gate (kalau backend berubah).
- Doc apa yang di-sync (atau "sudah sinkron, tak perlu update").
- Checklist PR `AGENTS.md` §11: item mana yang belum terpenuhi.
- Tegaskan: **tidak ada commit/push** dilakukan.
