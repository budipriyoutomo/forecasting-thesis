# AGENTS.md — ForecastIQ (Raw Material & Inventory Forecasting Platform, PPIC)

Dokumen ini adalah instruksi wajib untuk semua AI coding assistant (Claude Code dan lainnya) yang mengerjakan project ForecastIQ.
Baca seluruh dokumen ini — dan `docs/PRD.md` + `docs/ARCHITECTURE.md` — sebelum menulis satu baris kode pun.

> **Versi 2.0.** Dokumen ini adalah hasil rekonsiliasi antara draft AGENTS.md awal dan halaman Notion "Technical Documentation — ForecastIQ", yang ternyata berbeda di beberapa keputusan inti (model selection engine, data model, error codes). Lihat `docs/RECONCILIATION.md` untuk rincian setiap keputusan dan alasannya. Jika kamu menemukan instruksi lain (Notion, chat lama, dsb) yang bertentangan dengan dokumen ini, **dokumen ini yang menang** — laporkan konfliknya ke user, jangan diam-diam pilih salah satu.

---

## 1. Tentang Project Ini

**ForecastIQ** adalah platform forecasting berbasis AI untuk kebutuhan **raw material & inventory** tim PPIC (Production Planning & Inventory Control) — ditujukan untuk business user non-teknis (planner). User upload CSV berisi data historis konsumsi (bisa banyak SKU/material sekaligus dalam satu file), sistem secara otomatis **mengklasifikasikan pola demand tiap material**, **memilih metode forecasting terbaik per item** (Auto Model Selection), menghitung **safety stock & reorder point**, lalu menyajikan hasil lengkap dengan **penjelasan bahasa natural** — tanpa planner perlu paham statistik. Planner tetap bisa **override** rekomendasi sistem, dengan alasan & audit trail wajib.

Value proposition inti bukan sekadar "menjalankan forecast", tapi **mesin seleksi model otomatis yang akurat untuk pola demand tidak beraturan (khas raw material) dan bisa dipercaya & dijelaskan**.

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
| 2 | `docs/ARCHITECTURE.md` §4 Data Model | Schema tabel (Supabase Postgres) sebelum implement endpoint apapun |
| 3 | `docs/ARCHITECTURE.md` §5 API Contract | Format response & endpoint yang wajib diikuti semua endpoint |
| 4 | `docs/ARCHITECTURE.md` §6 Forecasting Engine | Detail teknis Auto Model Selection Engine (classification, scoring, registry) |
| 5 | `docs/ARCHITECTURE.md` §7 Storage Flow | Logic temp vs permanent file di Cloudflare R2 |
| 6 | `docs/ARCHITECTURE.md` §8 Error Handling | Aturan graceful error untuk semua kondisi |
| 7 | Section 3 di dokumen ini | TDD Workflow wajib sebelum implementasi |
| 8 | `docs/ARCHITECTURE.md` §3 | Struktur folder dan konvensi penamaan |
| 9 | `backend/app/services/forecasting/engines/README.md` | Sebelum menambah/ubah engine forecasting |
| 10 | `docs/RECONCILIATION.md` | Histori keputusan bila ada pertanyaan "kenapa begini bukan begitu" |

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
| ✅ Forbidden | User akses resource milik user lain → 403 |
| ✅ Not found | Resource ID (material/session/run) tidak ada → 404 |
| ✅ Validation error | CSV kosong, kolom wajib hilang, format tanggal salah → 400 |
| ✅ Insufficient data | Data historis di bawah `BACKTEST_MIN_PERIODS` → `INSUFFICIENT_DATA` |
| ✅ Model engine failure mock | Simulasi satu engine (ETS/Prophet/ARIMA/LightGBM/Croston) gagal saat backtest → exclude, lanjut kandidat lain |
| ✅ All engines fail | Semua kandidat gagal → `MODEL_SELECTION_FAILED` |
| ✅ Business logic | Validasi rule bisnis spesifik (contoh: `SESSION_EXPIRED`, override tanpa alasan → `OVERRIDE_REASON_REQUIRED`) |

### Coverage minimum (jalankan `pytest --cov=app --cov-report=term-missing`):
| Layer | Minimum |
|---|---|
| Endpoints (routes) | 90% |
| Services (business logic) | 85% |
| Forecasting engine module (classification, scoring, registry, factory) | 85% — gunakan mock/fixture data |
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
AUTH_INVALID_CREDENTIALS     AUTH_TOKEN_EXPIRED            AUTH_EMAIL_NOT_VERIFIED
MATERIAL_NOT_FOUND            UPLOAD_INVALID_FORMAT         UPLOAD_FILE_TOO_LARGE
SESSION_NOT_FOUND             SESSION_EXPIRED                INSUFFICIENT_DATA
MODEL_SELECTION_FAILED        FORECAST_RUN_NOT_FOUND         BACKTEST_FAILED
OVERRIDE_REASON_REQUIRED      STORAGE_UPLOAD_FAILED          RATE_LIMIT_EXCEEDED
UNSUPPORTED_FORECAST_METHOD
```
> Daftar ini final hasil penggabungan. Jangan tambah error code sepihak — kalau butuh code baru, tambahkan di sini dulu (dan di `ARCHITECTURE.md` §5) sebelum dipakai di kode.

### HTTP Status Code
`200` berhasil | `201` resource dibuat | `400` input validation error | `401` unauthorized | `403` forbidden | `404` not found | `422` invalid secara bisnis | `429` rate limit | `500` internal error | `503` dependency eksternal (Supabase/R2) unavailable

---

## 5. Aturan Auto Model Selection Engine + Manual Override

### Prinsip utama
- **Semua proses seleksi model harus melalui `app/services/forecasting/forecast_service.py`** — tidak boleh inline di router manapun.
- User **boleh memilih metode secara manual sebelum generate** (field `method` di request — lihat `docs/ARCHITECTURE.md` §6.8). Kalau `method` diisi, **skip** klasifikasi+scoring, langsung panggil fungsi metode itu. Kalau kosong/`null`, jalankan Auto Model Selection penuh.
- Kegagalan pada **mode manual TIDAK di-fallback** ke metode lain — user sudah memilih sadar, errornya harus jelas (`MODEL_SELECTION_FAILED` atau `UNSUPPORTED_FORECAST_METHOD`), bukan diam-diam diganti metode.
- Seleksi model **otomatis** wajib berbasis weighted scoring, bukan if-else rigid berdasarkan pola data.
- Nama/daftar metode aktif dan bobot scoring **tidak boleh hardcode tersebar di kode** — baca dari config/env (`FORECAST_ENGINES_ENABLED`, `SCORING_WEIGHT_*`), bisa diubah tanpa ubah kode.
- **Setiap metode forecasting (ETS, ARIMA, LightGBM, Croston/SBA, dan nanti Prophet) adalah SATU FUNGSI MURNI** — bukan class/Protocol. Signature seragam: `def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult`. Fungsi itu sendiri yang melakukan backtest (untuk MASE), fit ulang di seluruh data, predict horizon, dan generate explanation — semua self-contained di satu fungsi, satu file. Lihat `docs/ARCHITECTURE.md` §6.0/§6.6.
- Registry adalah `dict[str, Callable]` sederhana (`registry.py`) — **tidak ada `factory.py`** terpisah lagi karena tidak ada instansiasi class yang dibutuhkan (fungsi stateless).

### Alur seleksi model (wajib diikuti urutannya) — detail lengkap di `docs/ARCHITECTURE.md` §6
1. **Klasifikasi pola demand** — hitung ADI dan CV² → petakan ke kuadran Syntetos-Boylan: `smooth`, `erratic`, `intermittent`, `lumpy`.
2. **Filter engine kandidat** — hanya engine yang cocok dengan kuadran & minimum data requirement yang ikut kompetisi.
   > ⚠️ Kuadran `intermittent`/`lumpy` **wajib** punya kandidat `croston` — jangan sampai kuadran ini tanpa kandidat sama sekali (lihat gap yang dicatat di `RECONCILIATION.md`).
3. **Backtesting per engine kandidat** — rolling-origin backtest, hitung **MASE sebagai metrik utama** (bukan MAPE — MASE valid meski ada periode konsumsi nol, yang umum di raw material).
4. **Guardrail check** — cek bias dan tracking signal; engine dengan bias sistematis besar diberi penalti skor meski MASE rendah.
5. **Weighted scoring** — kombinasikan MASE, guardrail, dan kecocokan kuadran menjadi skor akhir per engine.
6. **Pilih skor tertinggi** → generate forecast final dari engine terpilih → generate natural language explanation dari hasil scoring.

### Struktur forecasting service (function registry, 1 fungsi = 1 metode)
```
backend/app/services/forecasting/
├── forecast_service.py     ← Orkestrasi utama: cabang manual (langsung panggil 1 fungsi) vs auto (klasifikasi → backtest → scoring)
├── classification.py       ← Hitung ADI/CV², mapping kuadran Syntetos-Boylan
├── scoring_engine.py       ← Weighted scoring (MASE + guardrail + fit kuadran) — hanya dipakai mode auto
├── types.py                ← ForecastPoint, EngineResult (dataclass, dipakai semua fungsi engine)
├── registry.py             ← MODEL_REGISTRY: dict[str, Callable] + filter per kuadran + get_enabled_methods()
└── engines/
    ├── README.md            ← WAJIB dibaca sebelum menambah/ubah engine
    ├── ets_engine.py        ← def forecast_ets(df, horizon) -> EngineResult
    ├── arima_engine.py      ← def forecast_arima(df, horizon) -> EngineResult
    ├── lightgbm_engine.py   ← def forecast_lightgbm(df, horizon) -> EngineResult
    ├── croston_engine.py    ← def forecast_croston(df, horizon) -> EngineResult (intermittent & lumpy)
    └── prophet_engine.py    ← TODO, belum diimplementasikan (dependency berat) — JANGAN didaftarkan di registry sampai selesai
```
> Post-MVP (tier lebih tinggi): `sarima_engine.py`, `holt_winters_engine.py`, `theta_engine.py`, `tbats_engine.py`, `neuralprophet_engine.py`, `xgboost_engine.py`, `lstm_engine.py`, `nhits_engine.py`, `tft_engine.py` — setiap satu tetap 1 fungsi, cukup didaftarkan ke `registry.py`, tidak boleh mengubah struktur `forecast_service.py`.

### Aturan failure engine (wajib diikuti)
| Kondisi | Tindakan |
|---|---|
| Satu engine gagal / timeout saat backtest | Exclude engine tersebut dari kompetisi, lanjutkan dengan engine lain, catat di log |
| Semua engine kandidat gagal | Return `MODEL_SELECTION_FAILED`, `forecast_results` untuk material tsb ditandai gagal (run lain tetap lanjut) |
| Data historis di bawah `BACKTEST_MIN_PERIODS` | Return `INSUFFICIENT_DATA` sebelum backtest dijalankan (fail fast) |
| Backtest per engine timeout | Timeout individual per engine (`ENGINE_TIMEOUT_SECONDS`), bukan timeout global |

> ⚠️ **Kegagalan satu engine tidak boleh menggagalkan seluruh proses seleksi.** Selama minimal satu engine kandidat berhasil di-backtest, proses seleksi tetap lanjut. **Kegagalan satu material tidak boleh menggagalkan seluruh forecast run** (run mencakup banyak material sekaligus).

### Planner Override — non-negotiable
- Setiap `forecast_result` dan `reorder_recommendation` **harus bisa di-override manual** oleh planner.
- Setiap override **wajib disertai audit trail**: siapa, kapan, nilai sebelum/sesudah, dan alasan (`OVERRIDE_REASON_REQUIRED` jika alasan kosong).
- Override tidak menghapus hasil forecast asli — disimpan sebagai baris baru di tabel `overrides` (append-only), bukan overwrite.

### Environment variables yang diperlukan
```env
# backend/.env
FORECAST_ENGINES_ENABLED=ets,arima,prophet,lgbm,croston   # daftar engine aktif — ganti di sini, 0 perubahan kode
SCORING_WEIGHT_MASE=0.6
SCORING_WEIGHT_GUARDRAIL=0.3
SCORING_WEIGHT_FIT=0.1
BACKTEST_MIN_PERIODS=12
ENGINE_TIMEOUT_SECONDS=45
FORECAST_TIMEOUT_SECONDS=120
MAX_UPLOAD_SIZE_MB=10

DATABASE_URL=postgresql://...
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
CLOUDFLARE_R2_ACCOUNT_ID=...
CLOUDFLARE_R2_ACCESS_KEY=...
CLOUDFLARE_R2_SECRET_KEY=...
CLOUDFLARE_R2_BUCKET_NAME=forecastiq-bucket
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

> 📌 Untuk MVP, job processing **synchronous**. Celery/Redis **tidak** diimplementasikan sampai ada sinyal kebutuhan real dari user (jangan tambahkan infrastruktur async secara prematur).

---

## 6. Data & Model Integrity

Dataset upload (CSV) dan hasil forecast adalah anchor kepercayaan planner — **tidak pernah dimodifikasi secara silent**.

### Yang boleh dilakukan sistem
- ✅ Validasi dan normalisasi format CSV (parsing tanggal, tipe data) — dengan log jelas apa yang diubah
- ✅ Generate forecast, confidence interval, dan natural language explanation
- ✅ Menyimpan revisi override sebagai entri baru dengan audit trail

### Yang dilarang keras
- ❌ Mengubah data historis (`consumption_history`) asli yang diupload user tanpa jejak (silent mutation)
- ❌ Overwrite `forecast_results`/`reorder_recommendations`/override sebelumnya tanpa menyimpan riwayat
- ❌ Auto-apply override planner ke material lain tanpa konfirmasi eksplisit

### Menambah/mengubah forecasting engine baru
> 📐 **Sebelum menulis atau mengubah file engine baru** (di `backend/app/services/forecasting/engines/`),
> WAJIB baca dulu **`backend/app/services/forecasting/engines/README.md`** — signature fungsi wajib
> (`def forecast_<method>(df, horizon) -> EngineResult`, self-contained: backtest + fit + predict + explanation
> dalam satu fungsi), minimum data requirement, kuadran demand yang didukung, dan cara registrasi ke `registry.py`.
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
| Service | snake_case + `_service` suffix | `forecast_service.py` |
| Model (ORM) | snake_case, noun singular | `forecast_result.py` |
| Schema (Pydantic) | snake_case, noun singular | `forecast.py` |
| Engine | snake_case + `_engine` suffix | `croston_engine.py` |
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
| 1 | ❌ Hardcode daftar engine/bobot scoring di kode | Harus bisa ganti/tuning tanpa ubah kode |
| 2 | ❌ Panggil logic forecasting langsung dari router | Semua proses harus melalui `forecast_service.py` |
| 3 | ❌ Modifikasi data historis asli tanpa jejak | Data & Model Integrity — dataset asli tidak boleh silent mutation |
| 4 | ❌ Expose stack trace ke client response | Log di server, return error code yang bersih ke client |
| 5 | ❌ Tulis implementasi sebelum test failing | TDD adalah workflow wajib |
| 6 | ❌ Commit file `.env` ke repo | Secret management — gunakan `.env.example` sebagai referensi |
| 7 | ❌ Merge PR jika coverage di bawah minimum | Quality gate yang tidak boleh dikompromikan |
| 8 | ❌ Satu engine/material gagal menggagalkan seluruh proses seleksi/run | Failure harus di-exclude, bukan menggagalkan proses lain |
| 9 | ❌ Override planner tanpa audit trail & alasan | Override tanpa jejak tidak diterima secara bisnis (PPIC adoption) |
| 10 | ❌ Simpan session/run state di backend memory | Backend harus stateless — semua state ada di Supabase |
| 11 | ❌ Menambahkan Celery/Redis di MVP tanpa sinyal kebutuhan nyata | Hindari premature infra complexity — sync-first untuk MVP |
| 12 | ❌ Membiarkan kuadran `intermittent`/`lumpy` tanpa engine kandidat | Croston/SBA wajib terdaftar — lihat §5 |
| 13 | ❌ Mengubah keputusan arsitektur di dokumen ini tanpa update `docs/RECONCILIATION.md` | Jejak keputusan harus tetap ada agar tidak ditanya ulang / diubah diam-diam |
| 14 | ❌ Fallback otomatis ke metode lain saat mode **manual** gagal | User sudah memilih sadar — error harus jelas, bukan diam-diam diganti (lihat §5) |
| 15 | ❌ Membuat engine baru sebagai class/Protocol | Kontrak final adalah 1 fungsi murni per metode (§5, §9) |

---

## 11. Checklist Sebelum Submit PR

- [ ] Semua test baru berjalan dengan status PASSED
- [ ] Coverage tidak turun di bawah minimum per layer
- [ ] Semua response mengikuti format Section 4
- [ ] Tidak ada hardcode daftar engine/bobot scoring di kode
- [ ] Proses seleksi model dilakukan melalui `forecast_service.py`, bukan inline
- [ ] Error handling mengikuti aturan Section 5 (failure per engine & per material)
- [ ] Tidak ada modifikasi silent pada data historis asli
- [ ] Override (jika ada) menyertakan audit trail lengkap
- [ ] File `.env` tidak ikut ter-commit
- [ ] Kuadran intermittent/lumpy tetap punya kandidat engine (croston terdaftar & aktif)
- [ ] Setiap metode forecasting baru adalah 1 fungsi (bukan class), sudah ada test-nya sendiri (`test_<method>_engine.py`)
- [ ] Mode manual (`method` diisi user) sudah diuji: sukses, error saat metode tidak dikenal (`UNSUPPORTED_FORECAST_METHOD`), dan tidak fallback saat gagal
