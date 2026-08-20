# AGENTS.md — ForecastIQ (ML Forecasting, Inventory Decision & Warehouse Capacity Constraint)

Dokumen ini adalah instruksi wajib untuk semua AI coding assistant (Claude Code dan lainnya) yang mengerjakan project ForecastIQ.
Baca seluruh dokumen ini — dan `docs/PRD.md` + `docs/ARCHITECTURE.md` — sebelum menulis satu baris kode pun.

> **Versi 3.0.** ForecastIQ dipivot menjadi **implementasi software dari metodologi Thesis** "Model Integrasi Machine Learning Forecasting dan Inventory Decision dengan Warehouse Capacity Constraint pada Produk Minuman RTD" (Noviana Asmoro, 2026). Lihat `docs/RECONCILIATION.md` §"Rekonsiliasi v3.0" untuk rincian setiap keputusan dan alasannya. Jika kamu menemukan instruksi lain (versi lama, chat lama, dsb) yang bertentangan dengan dokumen ini, **dokumen ini yang menang** — laporkan konfliknya ke user, jangan diam-diam pilih salah satu.

---

## 1. Tentang Project Ini

**ForecastIQ** adalah platform forecasting berbasis AI untuk kebutuhan **produk jadi (minuman RTD) dan material/packaging turunannya**, ditujukan untuk business user non-teknis (planner PPIC). User upload data historis **Forecast (existing) / Planning / Actual** per SKU produk jadi. Sistem **membandingkan 5 metode forecasting** (Moving Average, Exponential Smoothing, Random Forest, XGBoost, LSTM), memilih yang paling akurat berdasarkan backtest (MAD/MFE/MSE/MAPE), menurunkan **kebutuhan material via Bill of Materials (BOM)**, menghitung **safety stock, buffer stock, dan EOQ dinamis**, memvalidasi terhadap **kapasitas gudang**, dan mengoptimalkan **total biaya persediaan** — semua disajikan dengan **penjelasan bahasa natural**. Planner tetap bisa **override** rekomendasi sistem, dengan alasan & audit trail wajib.

Value proposition inti: **mesin forecasting yang secara sistematis membuktikan metode mana paling akurat untuk tiap SKU (dibanding metode existing perusahaan)**, terintegrasi dengan keputusan inventory yang **realistis secara fisik** (muat di gudang) dan **optimal secara biaya**.

**Monorepo structure:**
```
forecastiq/
├── frontend/     → Next.js (React, TypeScript, TanStack Query)
├── backend/      → FastAPI (Python)
├── docs/         → PRD, Architecture, Task Breakdown, Reconciliation
└── AGENTS.md     → (file ini)
```

## 2. Referensi Wajib (Baca Sebelum Coding)

| Urutan | Dokumen | Baca untuk |
|---|---|---|
| 1 | `docs/PRD.md` | Requirement produk, scope, user stories |
| 2 | `docs/ARCHITECTURE.md` §4 Data Model | Schema tabel (Supabase Postgres) — termasuk `products`, `boms`, `warehouse_config` — sebelum implement endpoint apapun |
| 3 | `docs/ARCHITECTURE.md` §5 API Contract | Format response & endpoint yang wajib diikuti semua endpoint |
| 4 | `docs/ARCHITECTURE.md` §6 Forecasting Engine | Detail teknis Comparative Selection Engine (evaluation, registry, engines) |
| 5 | `docs/ARCHITECTURE.md` §7 Storage Flow | Logic temp vs permanent file di object storage (S3-compatible) |
| 6 | `docs/ARCHITECTURE.md` §8 Error Handling | Aturan graceful error untuk semua kondisi |
| 7 | Section 3 di dokumen ini | TDD Workflow wajib sebelum implementasi |
| 8 | `docs/ARCHITECTURE.md` §3 | Struktur folder dan konvensi penamaan |
| 9 | `backend/app/services/forecasting/engines/README.md` | Sebelum menambah/ubah engine forecasting |
| 10 | `docs/RECONCILIATION.md` | Histori keputusan bila ada pertanyaan "kenapa begini bukan begitu", termasuk §"Rekonsiliasi v3.0" untuk konteks pivot ke metodologi thesis dan §"Rekonsiliasi v3.1" untuk merge dengan kode git aktual |

---

## 3. TDD — Aturan Tidak Dapat Dilanggar

TDD adalah **workflow wajib**, bukan opsional. Tidak ada implementasi tanpa test.

### Urutan yang benar: Red → Green → Refactor
```
🔴 RED     →  Tulis test untuk fitur yang BELUM ada. Test harus failing.
🟢 GREEN   →  Tulis implementasi MINIMUM yang membuat test passing. Tidak lebih.
🔵 REFACTOR →  Perbaiki kode tanpa mengubah behavior. Test harus tetap passing.
```

### Larangan keras:
- ❌ Jangan tulis implementasi sebelum ada test yang failing
- ❌ Jangan tulis lebih dari yang dibutuhkan untuk membuat test passing
- ❌ Jangan merge jika ada test yang failing

### Test wajib per endpoint (minimal):
| Test case | Deskripsi |
|---|---|
| ✅ Happy path | Input valid → response sesuai schema `ARCHITECTURE.md` §5 |
| ✅ Auth failure | Request tanpa token / token expired → 401 |
| ✅ Forbidden | User akses resource milik user lain → 403 `AUTH_FORBIDDEN` |
| ✅ Not found | Resource ID (product/material/session/run) tidak ada → 404 |
| ✅ Duplicate code | `code` produk/material sudah ada saat create/import → `PRODUCT_CODE_EXISTS` / `MATERIAL_CODE_EXISTS` |
| ✅ Validation error | CSV kosong, kolom wajib hilang, format tanggal salah → 400 |
| ✅ Insufficient data | Data historis di bawah `BACKTEST_MIN_PERIODS` (atau `LSTM_MIN_PERIODS` untuk LSTM) → `INSUFFICIENT_DATA` |
| ✅ Model engine failure mock | Simulasi satu engine (Moving Average/ES/Random Forest/XGBoost/LSTM) gagal saat backtest → exclude, lanjut kandidat lain |
| ✅ All engines fail | Semua kandidat gagal → `MODEL_SELECTION_FAILED` |
| ✅ BOM missing | Breakdown material diminta tapi produk belum punya BOM → `BOM_NOT_FOUND`, forecast produk tetap tersimpan |
| ✅ Warehouse capacity | Rekomendasi melebihi kapasitas gudang → flag `is_within_capacity = false`, bukan error block |
| ✅ Override target invalid | `target_id` override tidak ditemukan di tabel yang dirujuk `target_type` → `OVERRIDE_TARGET_NOT_FOUND` |
| ✅ Business logic | Validasi rule bisnis spesifik (contoh: `SESSION_EXPIRED`, override tanpa alasan → `OVERRIDE_REASON_REQUIRED`) |

### Coverage minimum (jalankan `pytest --cov=app --cov-report=term-missing`):
| Layer | Minimum |
|---|---|
| Endpoints (routes) | 90% |
| Services (business logic) | 85% |
| Forecasting engine module (evaluation, registry, tiap engine) | 85% — gunakan mock/fixture data |
| BOM / warehouse / EOQ / cost services | 85% — verifikasi manual hasil hitung |
| Storage service module | 80% — gunakan mock R2 |
| Database models | 70% |

---

## 4. API Response Standard

Base URL: `/api/v1`. Semua endpoint memerlukan `Authorization: Bearer {token}` kecuali auth endpoints. **Semua endpoint tanpa terkecuali** harus mengikuti format ini.

### Success
```json
{ "success": true, "data": {}, "message": "string (optional)" }
```

### Error
```json
{ "success": false, "error": { "code": "ERROR_CODE", "message": "Human readable message" } }
```

### Error codes yang valid (gunakan konstanta, bukan string bebas)
```
AUTH_INVALID_CREDENTIALS      AUTH_TOKEN_EXPIRED             AUTH_EMAIL_NOT_VERIFIED
AUTH_FORBIDDEN                 PRODUCT_CODE_EXISTS            MATERIAL_CODE_EXISTS
PRODUCT_NOT_FOUND              MATERIAL_NOT_FOUND             BOM_NOT_FOUND
UPLOAD_INVALID_FORMAT          UPLOAD_FILE_TOO_LARGE
SESSION_NOT_FOUND              SESSION_EXPIRED                 INSUFFICIENT_DATA
MODEL_SELECTION_FAILED         FORECAST_RUN_NOT_FOUND          BACKTEST_FAILED
UNSUPPORTED_FORECAST_METHOD    WAREHOUSE_CONFIG_NOT_FOUND      WAREHOUSE_CAPACITY_EXCEEDED
OVERRIDE_REASON_REQUIRED       OVERRIDE_TARGET_NOT_FOUND       STORAGE_UPLOAD_FAILED
RATE_LIMIT_EXCEEDED
```
> Daftar ini final hasil v3.1 (v3.0 + 4 code yang diwarisi dari implementasi v2.0 di git: `AUTH_FORBIDDEN`, `PRODUCT_CODE_EXISTS`, `MATERIAL_CODE_EXISTS`, `OVERRIDE_TARGET_NOT_FOUND` — lihat `RECONCILIATION.md` §"Rekonsiliasi v3.1"). Jangan tambah error code sepihak — kalau butuh code baru, tambahkan di sini dulu (dan di `ARCHITECTURE.md` §5) sebelum dipakai di kode. `WAREHOUSE_CAPACITY_EXCEEDED` dipakai sebagai *flag* di data response (200), **bukan** status error HTTP — lihat `ARCHITECTURE.md` §5.

### HTTP Status Code
`200` berhasil | `201` resource dibuat | `400` input validation error | `401` unauthorized | `403` forbidden | `404` not found | `422` invalid secara bisnis | `429` rate limit | `500` internal error | `503` dependency eksternal (Supabase/R2) unavailable

---

## 5. Aturan Forecasting Engine — Comparative Selection

### Prinsip utama
- **Semua proses forecasting harus melalui `app/services/forecasting/forecast_service.py`** — tidak boleh inline di router manapun.
- User **boleh memilih metode secara manual sebelum generate** (field `method` di request — lihat `docs/ARCHITECTURE.md` §6.6). Kalau `method` diisi, **skip** perbandingan, langsung panggil fungsi metode itu. Kalau kosong/`null`, jalankan **Comparative Selection** penuh (bandingkan seluruh metode aktif).
- Kegagalan pada **mode manual TIDAK di-fallback** ke metode lain — user sudah memilih sadar, errornya harus jelas (`MODEL_SELECTION_FAILED` atau `UNSUPPORTED_FORECAST_METHOD`), bukan diam-diam diganti metode.
- **Tidak ada klasifikasi pola demand (ADI/CV²/kuadran Syntetos-Boylan) di v3.0.** Comparative Selection menjalankan seluruh metode aktif dan memilih berdasarkan metrik akurasi (`FORECAST_RANKING_METRIC`, default MAPE terendah menang) — mengikuti metodologi Bab III thesis. Jangan tambahkan klasifikasi kuadran kembali tanpa didiskusikan dengan user dan dicatat di `RECONCILIATION.md`.
- Nama/daftar metode aktif **tidak boleh hardcode tersebar di kode** — baca dari config/env (`FORECAST_ENGINES_ENABLED`, `FORECAST_RANKING_METRIC`), bisa diubah tanpa ubah kode.
- **Setiap metode forecasting (Moving Average, Exponential Smoothing, Random Forest, XGBoost, LSTM) adalah SATU FUNGSI MURNI** — bukan class/Protocol. Signature seragam: `def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult`. Fungsi itu sendiri yang melakukan backtest (untuk MAD/MFE/MSE/MAPE), fit ulang di seluruh data, predict horizon, dan generate explanation — semua self-contained di satu fungsi, satu file. Lihat `docs/ARCHITECTURE.md` §6.0/§6.4.
- Registry adalah `dict[str, Callable]` sederhana (`registry.py`).
- Engine legacy (ETS/ARIMA/LightGBM/Croston/Prophet dari arsitektur v2.0) **tidak dihapus**, dipindah ke `engines/legacy/` dan nonaktif default — lihat `docs/ARCHITECTURE.md` §6.9. Jangan hapus file-file ini; cukup biarkan tidak terdaftar di `MODEL_REGISTRY` aktif.

### Alur seleksi model (wajib diikuti urutannya) — detail lengkap di `docs/ARCHITECTURE.md` §6
1. **Cek volume data** — `BACKTEST_MIN_PERIODS` (default 12), atau `LSTM_MIN_PERIODS` (default 24) khusus bila LSTM diminta/diikutkan. Di bawah minimum → `INSUFFICIENT_DATA`, fail fast.
2. **Mode manual**: panggil langsung 1 fungsi metode yang diminta, tanpa fallback.
3. **Mode otomatis**: jalankan seluruh metode aktif di `FORECAST_ENGINES_ENABLED` — tiap fungsi melakukan holdout backtest sendiri dan mengembalikan MAD/MFE/MSE/MAPE.
4. **Exclude yang gagal** — metode yang error saat backtest/fit dikeluarkan dari perbandingan, proses lanjut dengan sisanya.
5. **Ranking** — pilih metode dengan nilai `FORECAST_RANKING_METRIC` terbaik (default: MAPE terendah).
6. **Generate hasil final** dari metode terpilih → simpan seluruh `candidates_evaluated` (bukan cuma pemenang) untuk transparansi → generate natural language explanation yang membandingkan pemenang dengan kandidat lain.

### Struktur forecasting service (function registry, 1 fungsi = 1 metode)
```
backend/app/services/forecasting/
├── forecast_service.py     ← Orkestrasi utama: cabang manual (langsung panggil 1 fungsi) vs auto (jalankan semua & ranking)
├── evaluation.py           ← mad(), mfe(), mse(), mape() (+ mase() opsional)
├── types.py                ← ForecastPoint, EngineResult (dataclass, dipakai semua fungsi engine)
├── registry.py             ← MODEL_REGISTRY: dict[str, Callable] + get_enabled_methods()
└── engines/
    ├── README.md                          ← WAJIB dibaca sebelum menambah/ubah engine
    ├── moving_average_engine.py           ← def forecast_moving_average(df, horizon) -> EngineResult
    ├── exponential_smoothing_engine.py    ← def forecast_exponential_smoothing(df, horizon) -> EngineResult
    ├── random_forest_engine.py            ← def forecast_random_forest(df, horizon) -> EngineResult
    ├── xgboost_engine.py                  ← def forecast_xgboost(df, horizon) -> EngineResult
    ├── lstm_engine.py                     ← def forecast_lstm(df, horizon) -> EngineResult
    └── legacy/                            ← nonaktif default, lihat ARCHITECTURE.md §6.9
        ├── ets_engine.py
        ├── arima_engine.py
        ├── lightgbm_engine.py
        ├── croston_engine.py
        └── prophet_engine.py              ← TODO, belum diimplementasikan
```

### Aturan failure engine (wajib diikuti)
| Kondisi | Tindakan |
|---|---|
| Satu metode gagal / timeout saat backtest | Exclude metode tersebut dari perbandingan, lanjutkan dengan metode lain, catat di log |
| Semua metode kandidat gagal | Return `MODEL_SELECTION_FAILED`, `forecast_results` untuk produk tsb ditandai gagal (run lain tetap lanjut) |
| Data historis di bawah minimum periode | Return `INSUFFICIENT_DATA` sebelum backtest dijalankan (fail fast) |
| Backtest per metode timeout | Timeout individual per engine (`ENGINE_TIMEOUT_SECONDS` konvensional/tree, `LSTM_ENGINE_TIMEOUT_SECONDS` khusus LSTM), bukan timeout global |
| Produk tanpa BOM saat breakdown material diminta | Return `BOM_NOT_FOUND` untuk breakdown-nya saja — forecast produk tetap tersimpan sukses |
| Rekomendasi melebihi kapasitas gudang | **Bukan error** — flag `is_within_capacity = false`, planner tetap bisa lanjut (override) |

> ⚠️ **Kegagalan satu metode tidak boleh menggagalkan seluruh proses perbandingan.** Selama minimal satu metode berhasil di-backtest, proses seleksi tetap lanjut. **Kegagalan satu produk tidak boleh menggagalkan seluruh forecast run** (run mencakup banyak produk sekaligus).

### Planner Override — non-negotiable
- Setiap `forecast_result`, `material_requirement`, dan `reorder_recommendation` **harus bisa di-override manual** oleh planner.
- Setiap override **wajib disertai audit trail**: siapa, kapan, nilai sebelum/sesudah, dan alasan (`OVERRIDE_REASON_REQUIRED` jika alasan kosong).
- Override tidak menghapus hasil forecast asli — disimpan sebagai baris baru di tabel `overrides` (append-only), bukan overwrite.
- `target_id` override wajib divalidasi ada di tabel yang dirujuk `target_type` sebelum disimpan — kalau tidak ada, return `OVERRIDE_TARGET_NOT_FOUND`.

### Environment variables yang diperlukan
```env
# backend/.env
FORECAST_ENGINES_ENABLED=moving_average,exponential_smoothing,random_forest,xgboost,lstm
FORECAST_RANKING_METRIC=mape          # mape | mad | mse | mfe_abs — ganti di sini, 0 perubahan kode
COMPUTE_MASE=true
BACKTEST_MIN_PERIODS=12
LSTM_MIN_PERIODS=24
MOVING_AVERAGE_WINDOW=3
ENGINE_TIMEOUT_SECONDS=45
LSTM_ENGINE_TIMEOUT_SECONDS=120
FORECAST_TIMEOUT_SECONDS=180
MAX_UPLOAD_SIZE_MB=10

DEFAULT_ORDERING_COST=...
DEFAULT_HOLDING_COST_RATE=...
WAREHOUSE_PALLET_NO_RACKING=true

DATABASE_URL=postgresql://...
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
# Object storage S3-compatible (provider aktif: IDCloudHost). Endpoint dibaca utuh
# dari env — jangan diturunkan dari account ID provider tertentu di dalam kode.
S3_ENDPOINT_URL=https://is3.cloudhost.id
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=SouthJkt-a
S3_BUCKET_NAME=forecastiq-bucket
S3_ADDRESSING_STYLE=auto      # auto | path | virtual
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
```
```env
# frontend/.env.local
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_SUPABASE_URL=https://...
NEXT_PUBLIC_SUPABASE_ANON_KEY=...
```

> 📌 Untuk MVP, job processing **synchronous**. Celery/Redis **tidak** diimplementasikan sampai ada sinyal kebutuhan real dari user — training LSTM untuk banyak SKU sekaligus adalah kandidat pemicu paling mungkin, tapi jangan tambahkan infrastruktur async secara prematur.

---

## 6. Data & Model Integrity

Dataset upload (CSV: Forecast/Planning/Actual) dan hasil forecast adalah anchor kepercayaan planner — **tidak pernah dimodifikasi secara silent**.

### Yang boleh dilakukan sistem
- ✅ Validasi dan normalisasi format CSV (parsing tanggal, tipe data) — dengan log jelas apa yang diubah
- ✅ Generate forecast, confidence interval, breakdown BOM, dan natural language explanation
- ✅ Menyimpan revisi override sebagai entri baru dengan audit trail

### Yang dilarang keras
- ❌ Mengubah data historis (`demand_history`) asli yang diupload user tanpa jejak (silent mutation)
- ❌ Overwrite `forecast_results`/`material_requirements`/`reorder_recommendations`/override sebelumnya tanpa menyimpan riwayat
- ❌ Auto-apply override planner ke produk/material lain tanpa konfirmasi eksplisit
- ❌ Menghapus file engine legacy (`engines/legacy/`) — cukup biarkan nonaktif, jangan dihapus (lihat §5)

### Menambah/mengubah forecasting engine baru
> 📐 **Sebelum menulis atau mengubah file engine baru** (di `backend/app/services/forecasting/engines/`),
> WAJIB baca dulu **`backend/app/services/forecasting/engines/README.md`** — signature fungsi wajib
> (`def forecast_<method>(df, horizon) -> EngineResult`, self-contained: backtest + fit + predict + explanation
> dalam satu fungsi), minimum data requirement, dan cara registrasi ke `registry.py`.
> Tulis test dulu (`tests/unit/test_<method>_engine.py`) sebelum menulis fungsinya — TDD wajib (§3).

---

## 7. Storage Flow

Struktur folder R2 dan lifecycle file — lihat `docs/ARCHITECTURE.md` §7. Ringkasnya: `temp/uploads/{session_id}/...` (TTL 1 jam) → setelah validasi berhasil, **move** ke `permanent/datasets/{user_id}/{session_id}/raw.csv`. Forecast hasil → `permanent/forecasts/`. Export → `permanent/exports/`. Override audit trail → `permanent/overrides/`.

> ⚠️ Implement scheduled cleanup job yang baca `expires_at` dari tabel `upload_sessions` untuk hapus file temp yang sudah expired (cron setiap 30 menit).

---

## 8. Konvensi Penamaan

### Backend (Python/FastAPI)
| Layer | Konvensi | Contoh |
|---|---|---|
| Router | snake_case, noun plural, versioned di `api/v1/` | `api/v1/forecast.py` |
| Service | snake_case + `_service` suffix | `forecast_service.py`, `bom_service.py`, `warehouse_service.py` |
| Model (ORM) | snake_case, noun singular | `forecast_result.py` |
| Schema (Pydantic) | snake_case, noun singular | `forecast.py` |
| Engine | snake_case + `_engine` suffix | `random_forest_engine.py` |
| Test file | prefix `test_` | `test_forecast_service.py` |

### Frontend (TypeScript/Next.js)
| Layer | Konvensi | Contoh |
|---|---|---|
| Component | PascalCase | `ForecastChart.tsx` |
| Hook | camelCase + prefix `use` | `useForecastRun.ts` |
| Type/Interface | PascalCase | `ForecastResult.ts` |
| Service/API layer | camelCase | `forecastService.ts` |
| Util | camelCase | `formatDate.ts` |

---

## 9. Struktur Folder Referensi

Lihat `docs/ARCHITECTURE.md` §3 untuk struktur folder lengkap (frontend + backend). Jangan duplikasi di sini — kalau struktur berubah, update di `ARCHITECTURE.md`, bukan di dua tempat.

---

## 10. Hal yang Dilarang — Ringkasan

| # | Larangan | Alasan |
|---|---|---|
| 1 | ❌ Hardcode daftar engine/metrik ranking di kode | Harus bisa ganti/tuning tanpa ubah kode |
| 2 | ❌ Panggil logic forecasting langsung dari router | Semua proses harus melalui `forecast_service.py` |
| 3 | ❌ Modifikasi data historis asli tanpa jejak | Data & Model Integrity — dataset asli tidak boleh silent mutation |
| 4 | ❌ Expose stack trace ke client response | Log di server, return error code yang bersih ke client |
| 5 | ❌ Tulis implementasi sebelum test failing | TDD adalah workflow wajib |
| 6 | ❌ Commit file `.env` ke repo | Secret management — gunakan `.env.example` sebagai referensi |
| 7 | ❌ Merge PR jika coverage di bawah minimum | Quality gate yang tidak boleh dikompromikan |
| 8 | ❌ Satu engine/produk gagal menggagalkan seluruh proses seleksi/run | Failure harus di-exclude, bukan menggagalkan proses lain |
| 9 | ❌ Override planner tanpa audit trail & alasan | Override tanpa jejak tidak diterima secara bisnis (PPIC adoption) |
| 10 | ❌ Simpan session/run state di backend memory | Backend harus stateless — semua state ada di Supabase |
| 11 | ❌ Menambahkan Celery/Redis di MVP tanpa sinyal kebutuhan nyata | Hindari premature infra complexity — sync-first untuk MVP |
| 12 | ❌ Menghidupkan kembali klasifikasi ADI/CV²/kuadran tanpa diskusi & catatan di `RECONCILIATION.md` | v3.0 sudah pindah ke Comparative Selection sesuai metodologi thesis — jangan diam-diam kembali ke pendekatan lama |
| 13 | ❌ Mengubah keputusan arsitektur di dokumen ini tanpa update `docs/RECONCILIATION.md` | Jejak keputusan harus tetap ada agar tidak ditanya ulang / diubah diam-diam |
| 14 | ❌ Fallback otomatis ke metode lain saat mode **manual** gagal | User sudah memilih sadar — error harus jelas, bukan diam-diam diganti (lihat §5) |
| 15 | ❌ Membuat engine baru sebagai class/Protocol | Kontrak final adalah 1 fungsi murni per metode (§5, §9) |
| 16 | ❌ Menghapus file engine legacy (ETS/ARIMA/LightGBM/Croston) | Dipertahankan nonaktif untuk kasus raw material intermittent di luar scope thesis — lihat `ARCHITECTURE.md` §6.9 |
| 17 | ❌ Blocking rekomendasi yang melebihi kapasitas gudang sebagai hard error | Harus tetap flag & serahkan ke keputusan planner (override), bukan block otomatis |
| 18 | ❌ Membuat resource turunan (mis. reorder recommendation) hanya dengan `GET` tanpa `POST` generate | Resource yang dihitung dari forecast+BOM+request-time input (`current_stock`) wajib punya `POST` generate & persist dulu — lihat `ARCHITECTURE.md` §5 |
| 19 | ❌ Membuat `code` produk/material tanpa cek unik | Duplikat harus ditolak dengan `PRODUCT_CODE_EXISTS`/`MATERIAL_CODE_EXISTS`, bukan dibiarkan lolos ke database constraint error |

---

## 11. Checklist Sebelum Submit PR

- [ ] Semua test baru berjalan dengan status PASSED
- [ ] Coverage tidak turun di bawah minimum per layer
- [ ] Semua response mengikuti format Section 4
- [ ] Tidak ada hardcode daftar engine/metrik ranking di kode
- [ ] Proses forecasting dilakukan melalui `forecast_service.py`, bukan inline
- [ ] Error handling mengikuti aturan Section 5 (failure per engine & per produk)
- [ ] Tidak ada modifikasi silent pada data historis asli
- [ ] Override (jika ada) menyertakan audit trail lengkap, dan `target_id` divalidasi (`OVERRIDE_TARGET_NOT_FOUND` bila tidak ada)
- [ ] File `.env` tidak ikut ter-commit
- [ ] Breakdown BOM tetap tersimpan meski produk belum lengkap BOM-nya (bukan hard fail)
- [ ] Validasi kapasitas gudang menghasilkan flag, bukan block otomatis
- [ ] Setiap metode forecasting baru adalah 1 fungsi (bukan class), sudah ada test-nya sendiri (`test_<method>_engine.py`)
- [ ] Mode manual (`method` diisi user) sudah diuji: sukses, error saat metode tidak dikenal (`UNSUPPORTED_FORECAST_METHOD`), dan tidak fallback saat gagal
- [ ] Mode otomatis sudah diuji: `candidates_evaluated` tersimpan lengkap, ranking sesuai `FORECAST_RANKING_METRIC`
- [ ] Field `code` pada resource baru (produk/material/dsb) sudah dicek unik sebelum insert, dan pesan error mengikuti pola `*_CODE_EXISTS`
- [ ] Resource yang di-generate dari perhitungan (bukan CRUD murni) menyediakan endpoint `POST` untuk generate & persist sebelum `GET` untuk membaca — lihat `ARCHITECTURE.md` §5