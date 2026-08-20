# Task Breakdown & Roadmap Implementasi
## ForecastIQ — ML Forecasting, Inventory Decision & Warehouse Capacity Constraint (v3.1 — Rencana Migrasi)

> **Perubahan mendasar di revisi ini (v3.1):** dokumen ini **bukan lagi daftar fase greenfield**. Kode v2.0 (raw material, klasifikasi ADI/CV², engine ETS/ARIMA/LightGBM/Croston) **sudah selesai dibangun dan teruji** di repo GitHub (`budipriyoutomo/forecasting-thesis`) — Fase 0–8 versi lama sudah ✅ dengan migration, test, dan coverage tercatat di `docs/TASK_BREAKDOWN.md` (git). Keputusan user (25 Juli 2026, lihat `RECONCILIATION.md` §"Rekonsiliasi v3.1"): **migrasi/refactor codebase existing menuju v3.0**, bukan membangun ulang dari nol dan bukan menjalankan dua codebase paralel selamanya.
>
> Setiap task di bawah ini ditandai statusnya terhadap kode v2.0 yang sudah ada:
>
> | Tanda | Arti | Tindakan |
> |---|---|---|
> | 🟢 **DIPERTAHANKAN** | Kode v2.0 sudah benar, dipakai langsung di v3.0 | Tidak ada perubahan, atau perubahan kecil (rename/adjust) |
> | 🟡 **DIPERLUAS** | Kode v2.0 jadi basis, ditambah field/logic baru | Extend, jangan tulis ulang dari nol |
> | 🔴 **DIGANTI TOTAL** | Kode v2.0 tidak dipakai lagi di jalur aktif | Pindah ke `legacy/`, tulis implementasi baru dari nol (TDD) |
> | 🆕 **NET-NEW** | Tidak ada di v2.0 sama sekali | Bangun dari nol (TDD) |
>
> Setiap fase migrasi tetap mengikuti workflow TDD wajib di `AGENTS.md` §3 (Red → Green → Refactor). Jangan mulai fase migrasi berikutnya sebelum test fase sebelumnya PASSED dan coverage memenuhi minimum di `AGENTS.md` §3.

**Status per 4 Agustus 2026:** Fase Migrasi 0–9 ✅ SELESAI, cutover ke `main` sudah dilakukan (`7b20093`, `--no-ff`). Test suite hijau: **341 passed + 1 skipped (backend, coverage 92,4%)**, **63 passed / 18 file (frontend)**. Sisa satu item non-blocking di §10: verifikasi image Docker backend + TensorFlow untuk LSTM (deployment).

---

## 0. Strategi Migrasi — Branching, Parallel Testing, Cutover

Karena kode v2.0 sudah production-grade (bukan prototype), migrasi **tidak boleh** dilakukan dengan hapus-lalu-tulis-ulang di `main`. Urutan wajib:

1. **Branching**: buat branch `migration/v3-thesis` dari `main` (HEAD kode v2.0 yang sudah ✅ Fase 0–8). Semua kerja migrasi terjadi di branch ini, PR kecil per fase migrasi (lihat §1–§9 di bawah), bukan satu PR raksasa.
2. **Non-destructive first**: engine v2.0 (`ets_engine.py`, `arima_engine.py`, `lightgbm_engine.py`, `croston_engine.py`) dan `classification.py`/`scoring_engine.py` **dipindah** ke `engines/legacy/` dan **di-comment dari `MODEL_REGISTRY` aktif** — bukan dihapus (lihat `ARCHITECTURE.md` §6.9, `AGENTS.md` larangan #16). Ini membuat rollback trivial (uncomment) selama migrasi berlangsung.
3. **Migration DB additive dulu**: setiap migration Alembic baru (`products`, `boms`, `warehouse_config`, dst.) bersifat *additive* (tabel baru / kolom nullable baru) — jangan drop kolom/tabel v2.0 lama (`consumption_history`, dst.) sampai fase cutover (§9) selesai dan diverifikasi di lingkungan mendekati production.
4. **Parallel testing**: selama migrasi, test suite v2.0 lama (`test_forecast_api.py`, `test_material_api.py`, dst.) **tetap harus PASSED** — jangan dihapus sampai fitur yang digantikannya sudah punya test v3.0 yang setara. Jalankan `pytest` penuh (bukan cuma modul yang diubah) di tiap PR migrasi.
5. **Feature flag via env, bukan branch kode**: `FORECAST_ENGINES_ENABLED` menentukan engine mana yang aktif (lihat `ARCHITECTURE.md` §6.5). Ini dipakai juga sebagai *kill switch* selama masa transisi — kalau engine baru bermasalah di staging, kembalikan `FORECAST_ENGINES_ENABLED` ke daftar lama tanpa deploy ulang kode.
6. **Cutover terakhir, bukan pertama**: fase 9 (di bawah) adalah titik keputusan final — setelah seluruh fase migrasi lain selesai & diverifikasi, baru drop kolom/tabel v2.0 yang benar-benar tidak terpakai lagi dan merge `migration/v3-thesis` → `main`.

---

## 1. Fase Migrasi 0 — Setup Migrasi & Audit Kode Existing — ✅ SELESAI (25 Juli 2026)

- [x] Buat branch `migration/v3-thesis` dari `main`.
- [x] Audit & dokumentasikan inventaris kode v2.0 yang relevan (checklist, isi di PR pertama):
  - `backend/app/services/forecasting/registry.py`, `classification.py`, `scoring_engine.py` — 🔴 diganti (lihat §4)
  - `backend/app/services/forecasting/engines/ets_engine.py`, `arima_engine.py`, `lightgbm_engine.py`, `croston_engine.py` — 🔴 dipindah ke `legacy/` (lihat §4)
  - `backend/app/services/data_ingestion_service.py` — 🟡 diperluas (lihat §3)
  - `backend/app/services/storage_service.py` — 🟢 dipertahankan (lihat §3)
  - `backend/app/services/override_service.py` — 🟡 diperluas (lihat §8)
  - `backend/app/services/export_service.py` (jika ada, cek nama pasti di git) — 🟡 diperluas (lihat §10)
  - `backend/app/services/auth_service.py` — 🟢 dipertahankan (lihat §1)
  - `backend/app/utils/exceptions.py` — 🟡 diperluas (tambah exception class untuk error code baru)
  - `backend/alembic/versions/fae350da01a7_create_forecast_tables.py` (dan migration lain) — 🟢 dipertahankan sebagai riwayat, migration baru bersifat additive di atasnya
  - Dashboard/export/upload frontend scaffolding — 🟡 diperluas
- [x] Tambah `FORECAST_ENGINES_ENABLED`, `FORECAST_RANKING_METRIC`, dan env var baru lain (`ARCHITECTURE.md` §6.5) ke `.env.example` — belum aktif dipakai, hanya disiapkan. (+ `COMPUTE_MASE`, lihat `.env.example` baris 15–17.)
- [x] Pastikan seluruh test suite v2.0 lama PASSED di branch baru sebelum mulai fase migrasi berikutnya (baseline hijau).

**Selesai jika:** branch migrasi siap, inventaris kode existing terdokumentasi dengan status 🟢/🟡/🔴/🆕, baseline test v2.0 hijau di branch baru.

## 2. Fase Migrasi 1 — Auth 🟢 DIPERTAHANKAN — ✅ SELESAI (25 Juli 2026)

- [x] Verifikasi model `users`, Supabase Auth integration, endpoint `POST /api/v1/auth/login` & `GET /api/v1/auth/me`, RBAC dependency — **tidak ada perubahan skema atau logic**.
- [x] Tambah 1 hal baru: pastikan `AUTH_FORBIDDEN` (403, beda dari `AUTH_INVALID_CREDENTIALS`/`AUTH_TOKEN_EXPIRED` yang 401) sudah dipakai konsisten di seluruh endpoint baru v3.0 (products/materials/boms/warehouse/dst.) — cek apakah dependency RBAC v2.0 sudah return code ini atau perlu disesuaikan.
- [x] **TDD**: jalankan ulang test suite auth v2.0 existing, tambah test `AUTH_FORBIDDEN` untuk endpoint-endpoint baru di fase-fase berikutnya (bukan di fase ini).

**Selesai jika:** tidak ada regresi di auth, `AUTH_FORBIDDEN` terverifikasi konsisten dipakai di fase-fase baru selanjutnya.

## 3. Fase Migrasi 2 — Master Data: Produk (🆕), Material (🟡), BOM (🆕) — ✅ SELESAI (25 Juli 2026)

- [x] Model `materials` — 🟡 **diperluas** dari tabel material v2.0: tambah kolom `dimension` (JSONB `{length, width, height}`) dan `qty_per_pallet` (dipakai kalkulasi kapasitas gudang, §6). Migration additive (`ALTER TABLE ... ADD COLUMN`), bukan `DROP`+`CREATE`.
- [x] Model `products` — 🆕 net-new. `code` unik → `PRODUCT_CODE_EXISTS` jika duplikat (code baru, tambahkan ke `exceptions.py`).
- [x] Model `boms` — 🆕 net-new (product_id, material_id, qty_per_unit).
- [x] Endpoint `api/v1/products` (🆕, CRUD + import) dan `api/v1/boms` (🆕, CRUD + import). Endpoint `api/v1/materials` — 🟡 **diperluas** (tambah field dimension/qty_per_pallet ke request/response schema, cek apakah `MATERIAL_CODE_EXISTS` sudah ada di `exceptions.py` — sudah ada di git v2.0, tinggal dipakai konsisten di endpoint `products` juga).
- [x] **TDD**: test baru untuk `products`/`boms` (happy path, `PRODUCT_CODE_EXISTS`, `BOM_NOT_FOUND` referensi product_id/material_id tidak ada, `403 AUTH_FORBIDDEN`); test regresi untuk `materials` (field baru tidak merusak endpoint lama).
- [x] Frontend: halaman `products/` (🆕), `boms/` (🆕) — bisa reuse pola komponen tabel/form dari halaman `materials/` v2.0 yang sudah ada, jangan bangun dari nol.

**Selesai jika:** admin bisa kelola produk + BOM dari UI (baru), material v2.0 tetap berfungsi dengan field tambahan, tidak ada regresi test lama.

## 4. Fase Migrasi 3 — Data Ingestion & Historical Data (🟡 diperluas + rename) — ✅ SELESAI (25 Juli 2026)

- [x] Tabel `consumption_history` v2.0 → `demand_history` v3.0: **jangan rename kolom di tempat**. Buat tabel baru `demand_history` (migration additive) dengan kolom `product_id` (nullable, mengikuti pola `consumption_history.material_id` nullable v2.0 — lihat `RECONCILIATION.md` #14), `product_code` (snapshot), `forecast_existing`, `planning`, `actual`. Tulis script migrasi data satu-kali (bukan bagian dari alur aplikasi) untuk memindahkan histori lama jika relevan secara bisnis (didiskusikan dengan user — sebagian besar histori v2.0 adalah raw material, bukan produk jadi, jadi migrasi data historis mungkin **tidak berlaku** dan tabel baru dimulai kosong).
- [x] `data_ingestion_service.py` — 🟡 **diperluas**: logic parsing CSV & validasi kolom wajib v2.0 dipertahankan sebagai basis, tambah handling untuk 3 kolom paralel (`forecast_existing`/`planning`/`actual`) mengikuti struktur `Simulasi Thesis.xlsx` sheet "Bab I Plan vs Forecast", dan validasi terhadap `products.code` (bukan lagi hanya material code).
- [x] `storage_service.py` (R2 temp/permanent flow) — 🟢 **dipertahankan penuh**, tidak ada perubahan.
- [x] Model `upload_sessions` — 🟢 **dipertahankan**, hanya `n_products_detected` (rename dari field serupa jika perlu, cek nama field aktual di git) menyesuaikan istilah produk vs material.
- [x] **TDD**: test regresi upload v2.0 (format lama masih jalan jika masih dipakai untuk raw material — lihat §Keputusan Terbuka `RECONCILIATION.md` poin 1), test baru untuk 3-kolom produk jadi.

**Selesai jika:** upload CSV 3-kolom (Forecast existing/Planning/Actual) per produk jadi tervalidasi dan tersimpan di `demand_history`, storage flow tidak ada regresi.

## 5. Fase Migrasi 4 — Forecasting Engine (🔴 DIGANTI TOTAL — perubahan paling signifikan) — ✅ SELESAI (25 Juli 2026)

- [x] **Pindahkan, jangan hapus**: `classification.py`, `scoring_engine.py` (ADI/CV² → kuadran Syntetos-Boylan) — sudah tidak dipanggil di pipeline v3.0 (`ARCHITECTURE.md` §6 comparative selection tidak pakai klasifikasi). Simpan sebagai referensi/kemungkinan reuse untuk raw material forecasting di luar scope thesis (`RECONCILIATION.md` Keputusan Terbuka v3.0 poin 2) — jangan hapus filenya, tapi juga jangan dipanggil dari `forecast_service.py` baru.
- [x] **Pindahkan** `engines/ets_engine.py`, `engines/arima_engine.py`, `engines/lightgbm_engine.py`, `engines/croston_engine.py` → `engines/legacy/` (fisik pindah folder, bukan hapus). Comment dari `MODEL_REGISTRY` aktif (`ARCHITECTURE.md` §6.3).
- [x] `metrics.py` v2.0 (`mean_absolute_scaled_error`, `train_test_split_series` — lihat `engines/README.md` git) — 🟡 **diperluas** jadi basis `evaluation.py` baru: `mase()` (fungsi MASE lama) dipertahankan sebagai opsional (`COMPUTE_MASE` env), ditambah `mad()`, `mfe()`, `mse()`, `mape()` baru (fungsi murni, TDD dari nol karena belum ada di v2.0).
- [x] `preprocessing.py` (`to_daily_series` — lihat `engines/README.md` git) — 🟢 **dipertahankan** bila reusable untuk preprocessing data harian; sesuaikan bila engine baru butuh periode bulanan (data thesis per bulan, bukan harian — cek asumsi ini dengan data `Simulasi Thesis.xlsx`).
- [x] 🆕 **NET-NEW**, tulis dari nol dengan TDD (urutan disarankan — mulai dari yang paling sederhana ke kompleks):
  - [x] `moving_average_engine.py`
  - [x] `exponential_smoothing_engine.py`
  - [x] `random_forest_engine.py`
  - [x] `xgboost_engine.py`
  - [x] `lstm_engine.py` (paling kompleks, butuh TensorFlow — verifikasi build Docker dulu, lihat §9)
- [x] `registry.py` — 🔴 **ditulis ulang**: dari klasifikasi-berbasis-kuadran ke `dict[str, Callable]` datar sesuai `ARCHITECTURE.md` §6.3. Struktur dict lama bisa jadi referensi pola, tapi isi & alur pemilihannya beda total.
- [x] `forecast_service.py` — 🔴 **ditulis ulang**: orkestrasi lama (routing by kuadran) diganti Comparative Selection (`ARCHITECTURE.md` §6.1). **PENTING**: endpoint & response contract (`POST /api/v1/forecast/runs`, format `forecast_results`) sebisa mungkin **dipertahankan bentuknya** supaya frontend `forecast/` yang sudah ada tidak perlu ditulis ulang total — hanya field baru (`selection_mode`, `candidates_evaluated`, `mad`/`mfe`/`mse`/`mape`) yang ditambahkan.
- [x] Model `forecast_results` — 🟡 **diperluas**: tambah kolom `selection_mode`, `candidates_evaluated` (JSONB), `mad`/`mfe`/`mse`/`mape`, `mase` (nullable). `method_used` berubah domain nilai (dulu ets/arima/lightgbm/croston, sekarang moving_average/exponential_smoothing/random_forest/xgboost/lstm) — **bukan breaking di level kolom** (masih VARCHAR), tapi breaking di level nilai yang valid; dokumentasikan di changelog migration.
- [x] Frontend: `MethodSelector.tsx` — 🟡 diperluas (ganti daftar dropdown metode, dari nama kuadran ke 5 metode + opsi "Bandingkan Otomatis"). Komponen chart/tabel hasil forecast — 🟢 dipertahankan strukturnya, hanya sumber data field yang berubah.
- [x] **TDD menyeluruh** (prioritas tertinggi di seluruh migrasi): test tiap engine baru dengan fixture; test mode manual & otomatis; test `MODEL_SELECTION_FAILED`; test `INSUFFICIENT_DATA`/`LSTM_MIN_PERIODS`; **hapus/nonaktifkan test v2.0 yang spesifik ke klasifikasi ADI/CV² hanya setelah** confirmed tidak ada lagi jalur kode yang memanggilnya.

**Selesai jika:** forecast run end-to-end pakai 5 metode baru (comparative + manual), `candidates_evaluated` tersimpan, engine v2.0 lama masih ada di `legacy/` tapi tidak terpanggil di jalur aktif, coverage ≥ 85%.

## 6. Fase Migrasi 5 — BOM Breakdown, Safety Stock, Buffer Stock & EOQ (🟡 diperluas + 🆕 net-new) — ✅ SELESAI (25 Juli 2026)

- [x] `bom_service.py` — 🆕 net-new (belum ada konsep BOM di v2.0 raw-material-langsung).
- [x] Model `material_requirements` — 🆕 net-new.
- [x] `reorder_service.py` — 🟡 **diperluas**: safety stock (`SS = Z × STD × √L`) v2.0 kemungkinan sudah ada logicnya (cek implementasi aktual di git) — **dipertahankan** sebagai basis. Buffer stock dan **EOQ dinamis** (`TC = nS + Σ(Iₜ×H)`) adalah 🆕 net-new, ditambahkan ke service yang sama.
- [x] Model `reorder_recommendations` — 🟡 **diperluas**: tambah kolom `buffer_stock`, `eoq_qty`, `ordering_cost`, `holding_cost`, `total_inventory_cost`. `current_stock` **bukan** kolom baru — dikirim sebagai request param di endpoint generate (lihat §7 di bawah), bukan disimpan.
- [x] **Endpoint reorder — cek & perbaiki pola git**: git v2.0 sudah punya `POST /api/v1/reorder/recommendations` (generate+persist, dengan `current_stock`) selain `GET`. Pastikan pola ini **dipertahankan** di v3.0 (jangan turun jadi `GET`-only) — ini sudah diterapkan di `ARCHITECTURE.md` §5 v3.1, tinggal pastikan implementasi kode ikut.
- [x] **TDD**: skenario lead time, MOQ, demand stabil/volatile; `BOM_NOT_FOUND` (forecast tetap tersimpan); verifikasi manual perhitungan EOQ.

**Selesai jika:** kebutuhan material terhitung dari forecast × BOM, buffer stock & EOQ benar secara matematis, endpoint `POST`+`GET` reorder konsisten dengan pola git v2.0.

## 7. Fase Migrasi 6 — Validasi Kapasitas Gudang (🆕 NET-NEW — sesuai judul thesis) — ✅ SELESAI (25 Juli 2026)

- [x] Model `warehouse_config`, `warehouse_validations` — 🆕 net-new, tidak ada padanan di v2.0.
- [x] `warehouse_service.py` — 🆕 net-new: `compute_pallet_capacity()`, `compute_material_capacity()`, `validate_capacity()` (`ARCHITECTURE.md` §6.7).
- [x] Endpoint `GET/PUT /api/v1/warehouse/config`, `GET /api/v1/forecast/runs/{run_id}/warehouse-validation` — 🆕.
- [x] **TDD**: kapasitas cukup/tidak cukup, berbagai dimensi palet — verifikasi hitung manual.
- [x] Frontend: halaman `warehouse/` (🆕), indikator visual di halaman hasil forecast/reorder yang sudah ada (🟡 diperluas, tambah badge, bukan halaman baru).

**Selesai jika:** validasi kapasitas gudang berbasis palet berjalan dan tampil sebagai flag non-blocking di UI existing.

## 8. Fase Migrasi 7 — Optimasi Total Biaya & Evaluasi Kinerja Inventory (🆕 NET-NEW) — ✅ SELESAI (26 Juli 2026)

- [x] `cost_service.py` — 🆕 net-new: agregasi TIC usulan vs baseline + `compute_savings_pct()`. **Rumus TIC/EOQ/savings di-reuse dari `reorder_service.py`, tidak diduplikasi** (RECONCILIATION §Fase 7).
- [x] `inventory_metrics_service.py` — 🆕 net-new: Service Level, Fill Rate, Stock Out Rate, Inventory Turnover (fungsi murni + orkestrasi 2 scope).
- [x] Model `inventory_metrics` — 🆕 net-new (+ kolom `scope` `baseline`/`forecastiq`, additive; migration `a7b8c9d0e1f2`).
- [x] Endpoint `GET /forecast/runs/{run_id}/cost-summary`, `GET /forecast/runs/{run_id}/inventory-metrics` — 🆕.
- [x] **TDD**: rumus tiap metrik diverifikasi manual (`test_inventory_metrics_service.py`, `test_cost_service.py`, `test_metrics_api.py`, `test_inventory_metrics_repository.py`). Rumus 4 metrik tak ada di Bab III/`Simulasi Thesis.xlsx` → definisi standar disepakati user & dicatat di RECONCILIATION §Fase 7.

**Selesai:** tiap forecast run menghasilkan TIC + % penghematan + 4 metrik kinerja (scope baseline & forecastiq) yang terverifikasi manual; 322 test PASSED, coverage service 98–100%, route 100%, repo 100%.
> **Frontend belum**: widget cost-summary & inventory-metrics di dashboard/laporan masuk Fase 9 (dashboard diperluas). Backend Fase 7 lengkap.

## 9. Fase Migrasi 8 — Planner Override & Audit Trail (🟡 DIPERLUAS) — ✅ SELESAI (26 Juli 2026)

- [x] Model `overrides`, `override_service.py` — 🟢 **dipertahankan** sepenuhnya (append-only, `reason` wajib, `OVERRIDE_REASON_REQUIRED` sudah ada di v2.0). Tanpa perubahan skema.
- [x] 🆕 tambahan: `target_type` kini bisa merujuk `material_requirement` — resolver + snapshot builder + Literal schema diperluas satu entri (RECONCILIATION §Fase 8). Resolver pakai `SqlMaterialRequirementRepository.get_requirement` (sudah ada Fase 5).
- [x] 🆕 tambahan: `OVERRIDE_TARGET_NOT_FOUND` tervalidasi juga untuk `material_requirement` (tak ada error code baru).
- [x] **TDD**: regresi override lama tetap PASSED; test baru `test_create_override_material_requirement_snapshot`, `..._target_tidak_ada_404` (service) + `test_create_override_material_requirement_201` (API).

**Selesai:** override berfungsi untuk seluruh entitas v3.0 (forecast_result, reorder_recommendation, material_requirement); tidak ada regresi; `override_service` coverage 100%.

## 10. Fase Migrasi 9 — Dashboard, Export & Cutover Final — ✅ SELESAI (27 Juli 2026), sisa 2 item non-blocking

- [x] Dashboard (`dashboard/summary`) — 🟡 **diperluas** (backend): scaffolding v2.0 dipertahankan, ditambah `total_inventory_cost` run terakhir, `avg_mape`, indikator kapasitas gudang (`warehouse`), ringkasan metrik inventory per scope (`inventory_metrics`). Repo warehouse/metrics opsional → additive, tanpa regresi (RECONCILIATION §Fase 9).
- [x] Export service — 🟡 **diperluas**: kolom `buffer_stock`/`eoq_qty`/`ordering_cost`/`holding_cost`/`total_inventory_cost` ditambah ke reorder xlsx **setelah** kolom lama (status tetap kolom 5 → backward compat).
- [x] Frontend: widget `cost-summary` & `inventory-metrics` — `CostSummaryCard.tsx`, `InventoryMetricsTable.tsx` + hook `useMetrics.ts` + `api.metrics` + types + vitest (4 test, hijau). Dirakit ke halaman hasil forecast (`forecast/new/config`), tampil setelah reorder dihitung. `ExplanationBox`/pages produk/BOM/warehouse sudah dari fase sebelumnya.
- [x] **Susulan (4 Agustus 2026)** — `GET /forecast/runs/{run_id}/material-requirements`: sudah ada di kontrak `ARCHITECTURE.md` §5 sejak v3.1 tapi **tak pernah diimplementasi**, sehingga `SqlMaterialRequirementRepository.list_by_run` jadi dead code dan planner tak punya `target_id` untuk override `material_requirement` (melanggar `AGENTS.md` §5 "Planner Override — non-negotiable"). Ditambah: `ForecastRunService.list_requirements` + `MaterialRequirementOut` + endpoint (8 test backend), `OverrideTargetType` frontend disamakan dengan `schemas/override.py`, `MaterialRequirementsTable.tsx` + `useMaterialRequirements` + `api.forecast.materialRequirements` (6 test frontend), dirakit ke halaman `forecast/new/config` antara hasil forecast & reorder.
- [x] **Bugfix (4 Agustus 2026)** — cron `cleanup_temp_uploads` merakit `UploadService(consumptions=…, materials=…)`, sisa rename v3.0 (signature sudah `demand`/`products`) → `TypeError` tiap job jalan, file temp R2 **tidak pernah dibersihkan** (FR-1.5 mati diam-diam). Lolos 340 test karena `test_cleanup_job.py` memonkeypatch `UploadService` dengan `lambda **kw` yang menelan keyword apa pun; diganti `create_autospec` supaya drift signature ketahuan. Job kini pakai `SqlDemandHistoryRepository`/`SqlProductRepository`.
- [x] `ExplanationBox` — logic penjelasan Comparative Selection. **Selesai 4 Agustus 2026**: `forecast_service` kini menempelkan narasi dasar pemilihan di depan penjelasan engine (pemenang, jumlah metode dibandingkan, metrik ranking + nilai, runner-up) — mode manual tidak ditempeli. Frontend: `CandidatesTable.tsx` merender `candidates_evaluated` (sebelumnya tersimpan di DB tapi tak pernah tampil) sebagai tabel terurut + badge pemenang, dirakit di `ForecastResults`. 2 test backend + 4 test frontend.
- [x] **Cutover checklist** (lihat §0 poin 6) — disetujui user 27 Juli 2026:
  - [x] Seluruh fase migrasi 1–8 PASSED (332 backend + 53 frontend hijau).
  - [ ] Verifikasi image Docker backend dengan TensorFlow (LSTM) build & run — **belum**. Update 20 Agustus 2026: artefak deployment VPS sudah dibuat (Dockerfile backend & frontend, `.dockerignore`, `docker-compose.prod.yml`, `Caddyfile`, entrypoint migrasi — lihat `RECONCILIATION.md` §Deployment VPS dan `ARCHITECTURE.md` §10), tapi image belum pernah benar-benar di-build karena Docker daemon mati di mesin dev. TensorFlow tetap di-comment; `lstm` sengaja dikeluarkan dari `FORECAST_ENGINES_ENABLED` di `.env.prod.example`.
  - [x] Drop kolom v2.0 yang aman: `forecast_results.data_profile` + `material_id` (migration `b8c9d0e1f2a3`, reversible). `consumption_history` awalnya dipertahankan, lalu **di-drop 4 Agustus 2026** (migration `c9d0e1f2a3b4`) setelah audit membuktikan jalur raw-material v2.0 sudah mati total — alasan lengkap di `RECONCILIATION.md` §Pensiun Jalur Raw-Material v2.0.
  - [x] Merge `migration/v3-thesis` → `main` (`--no-ff`).
  - [x] Status migrasi dicatat di dokumen ini + `RECONCILIATION.md`.

**Selesai:** aplikasi v3.0 berjalan penuh, dashboard & export mencerminkan seluruh fitur baru, cutover ke `main` selesai dengan jejak keputusan lengkap di `RECONCILIATION.md`. Sisa non-blocking: wiring UI lanjutan & verifikasi image Docker LSTM (deployment).

---

## Prioritas Jika Waktu Terbatas (MVP Migrasi Tercepat)

1. Fase Migrasi 0 (setup & audit — wajib, jangan dilewati meski buru-buru, ini yang mencegah migrasi jadi rewrite liar)
2. Fase Migrasi 2 (produk + BOM, versi sederhana — material sudah ada, tinggal diperluas)
3. Fase Migrasi 3 (ingestion 3-kolom)
4. **Fase Migrasi 4 (Forecasting Engine — jangan dilewati meski buru-buru; ini inti klaim akademik & produk, dan risiko migrasi tertinggi)**
5. Fase Migrasi 5 (BOM breakdown + safety/buffer stock + EOQ, versi sederhana)
6. Fase Migrasi 6 (Warehouse Capacity — minimal validasi dasar, komponen khas judul thesis)
7. Fase Migrasi 9 bagian dashboard (versi sederhana, cutover penuh menyusul)

Fase Migrasi 1 (auth — sudah 🟢, hampir tanpa kerja tambahan), Fase Migrasi 7 (cost & inventory metrics lengkap), Fase Migrasi 8 (override untuk entitas baru), dan cutover penuh di Fase Migrasi 9 bisa menyusul setelah MVP migrasi tervalidasi.

---
*Lihat `RECONCILIATION.md` §"Rekonsiliasi v3.0" untuk alasan perubahan metodologi (v2.0→v3.0) dan §"Rekonsiliasi v3.1" untuk keputusan migrasi kode existing serta merge dengan dokumen git aktual.*