# Dokumen Arsitektur Teknis
## ForecastIQ — Raw Material & Inventory Forecasting Platform (PPIC)

| | |
|---|---|
| **Versi** | 2.0 (merged — lihat `RECONCILIATION.md`) |
| **Tanggal** | 23 Juli 2026 |
| **Terkait** | `PRD.md`, `AGENTS.md` (instruksi coding), `RECONCILIATION.md` |

---

## 1. Ringkasan Arsitektur

```
┌─────────────────────┐        HTTPS/REST (/api/v1)     ┌──────────────────────┐
│  Frontend (Next.js)  │ <──────────────────────────────> │  Backend (FastAPI)   │
│  Vercel               │                                  │  Railway              │
└─────────────────────┘                                  └──────────┬───────────┘
                                                                     │
                                    ┌────────────────────────────────┼────────────────────────┐
                                    │                                │                        │
                          ┌─────────▼─────────┐          ┌───────────▼──────────┐   ┌──────────▼─────────┐
                          │ PostgreSQL (Supabase) │       │ Cloudflare R2         │   │ Supabase Auth (JWT) │
                          │ materials, uploads,   │       │ temp/ + permanent/    │   │                     │
                          │ forecast_runs/results,│       │ CSV & export files    │   │                     │
                          │ reorder, overrides    │       └───────────────────────┘   └─────────────────────┘
                          └───────────────────────┘
```

### Prinsip Arsitektur
- **Stateless backend** — semua state di database, tidak ada session di memory server.
- **Synchronous untuk MVP** — forecasting dijalankan sync; Celery/Redis ditambahkan hanya jika ada sinyal kebutuhan nyata.
- **Registry/Factory pattern untuk model engine** — tambah engine baru = tambah class + daftar di registry, tanpa ubah orchestrator/endpoint/test.
- **Orkestrasi terpusat** — semua proses seleksi model wajib melalui `forecast_service.py`, tidak boleh inline di router.
- **Data & Model Integrity** — data historis asli & hasil forecast/override tidak pernah di-overwrite secara silent.
- **TDD sebagai workflow wajib** — lihat `AGENTS.md` §3.

## 2. Tech Stack

| Layer | Teknologi | Hosting |
|---|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind + shadcn/ui + TanStack Query | Vercel |
| Backend | FastAPI (Python 3.11+) + Pydantic v2 + SQLAlchemy 2.0 async | Railway |
| Database | PostgreSQL | Supabase |
| Object Storage | Cloudflare R2 (CSV upload & export) | Cloudflare |
| Auth | Supabase Auth (JWT) | Supabase |
| Forecasting | statsmodels (ETS/ARIMA), Prophet, LightGBM, **implementasi Croston/SBA custom** (lihat §6.6) | Backend (bundled) |
| Testing | pytest + pytest-cov (backend), Vitest + RTL (frontend) | CI |

## 3. Struktur Folder (Monorepo)

```
forecastiq/
├── AGENTS.md                        ← Instruksi wajib untuk AI coding assistant (final, hasil rekonsiliasi)
├── README.md
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md              ← dokumen ini
│   ├── TASK_BREAKDOWN.md
│   └── RECONCILIATION.md
│
├── frontend/                        ← Next.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/login/  register/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── dashboard/
│   │   │   │   ├── materials/          ← master data material (khusus domain PPIC)
│   │   │   │   ├── forecast/new/       ← upload + konfigurasi
│   │   │   │   ├── forecast/[id]/      ← hasil forecast per run
│   │   │   │   └── settings/
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/
│   │   │   ├── upload/
│   │   │   ├── config/
│   │   │   ├── forecast/
│   │   │   ├── materials/              ← CRUD master data material
│   │   │   ├── override/               ← planner override & audit trail UI
│   │   │   └── dashboard/
│   │   ├── lib/{api.ts, utils.ts}
│   │   ├── hooks/{useUpload.ts, useForecastRun.ts, useOverride.ts, useAuth.ts}
│   │   └── types/
│   └── package.json
│
├── backend/                          ← FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/v1/
│   │   │   ├── auth.py
│   │   │   ├── materials.py
│   │   │   ├── uploads.py
│   │   │   ├── forecast.py
│   │   │   ├── reorder.py
│   │   │   └── overrides.py
│   │   ├── services/
│   │   │   ├── forecasting/
│   │   │   │   ├── forecast_service.py     ← orkestrasi (satu-satunya entry point)
│   │   │   │   ├── classification.py       ← ADI/CV² → kuadran Syntetos-Boylan
│   │   │   │   ├── scoring_engine.py       ← weighted scoring (MASE + guardrail + fit)
│   │   │   │   ├── registry.py             ← MODEL_REGISTRY
│   │   │   │   ├── factory.py              ← instansiasi engine dari registry
│   │   │   │   └── engines/
│   │   │   │       ├── README.md           ← kontrak base_engine, cara tambah engine baru
│   │   │   │       ├── base_engine.py      ← Protocol: fit, predict, backtest, get_explanation
│   │   │   │       ├── ets_engine.py
│   │   │   │       ├── prophet_engine.py
│   │   │   │       ├── arima_engine.py
│   │   │   │       ├── lightgbm_engine.py
│   │   │   │       └── croston_engine.py   ← Croston/SBA untuk intermittent & lumpy demand
│   │   │   ├── data_ingestion_service.py   ← parsing & validasi CSV
│   │   │   ├── reorder_service.py          ← safety stock & reorder point
│   │   │   ├── override_service.py
│   │   │   ├── storage_service.py          ← Cloudflare R2
│   │   │   └── auth_service.py
│   │   ├── models/                         ← SQLAlchemy ORM models
│   │   ├── schemas/                        ← Pydantic request/response
│   │   ├── db/{session.py, models.py}
│   │   └── utils/{auth.py, exceptions.py, explainer.py}
│   ├── alembic/
│   ├── tests/
│   │   ├── conftest.py
│   │   ├── unit/
│   │   └── integration/
│   ├── pyproject.toml
│   └── Dockerfile
│
└── docker-compose.yml
```

## 4. Data Model (Final — Merged)

### `users`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| email | VARCHAR(255) UNIQUE | |
| name | VARCHAR(100) | |
| role | VARCHAR(20) | admin / ppic / purchasing / viewer |
| is_verified | BOOLEAN | default false |
| created_at / updated_at | TIMESTAMPTZ | |

### `materials`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| code | VARCHAR unique | kode material |
| name | VARCHAR | |
| category | VARCHAR | |
| unit | VARCHAR | satuan |
| lead_time_days | INTEGER | |
| moq | NUMERIC | minimum order quantity |
| manual_safety_stock | NUMERIC, nullable | override manual |
| created_at / updated_at | TIMESTAMPTZ | |

### `upload_sessions`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| user_id | UUID FK → users | |
| file_name | VARCHAR | |
| file_url | TEXT | URL di R2 (temp atau permanent) |
| file_size_kb | INTEGER | |
| n_rows | INTEGER | |
| n_materials_detected | INTEGER | |
| preview_data | JSONB | 5 baris pertama |
| warnings | JSONB, nullable | |
| status | VARCHAR(20) | pending / validated / failed / expired |
| created_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ | created_at + 1 jam (jika belum divalidasi) |

### `consumption_history`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| material_id | UUID FK → materials | |
| date | DATE | |
| quantity | NUMERIC | |
| upload_session_id | UUID FK → upload_sessions | |

### `forecast_runs`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| user_id | UUID FK → users | trigger by |
| horizon | INTEGER | |
| horizon_unit | VARCHAR(10) | days / weeks / months |
| status | VARCHAR(20) | PENDING / PROCESSING / COMPLETED / FAILED |
| created_at / completed_at | TIMESTAMPTZ | |
| error_message | TEXT, nullable | |

> Satu `forecast_run` mencakup **banyak material sekaligus** (bukan 1 run = 1 item), sesuai realita upload PPIC yang berisi banyak SKU dalam satu file.

### `forecast_results`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| run_id | UUID FK → forecast_runs | |
| material_id | UUID FK → materials | |
| data_profile | JSONB | `{n_points, adi, cv2, demand_class, has_seasonality, is_stationary, missing_ratio, has_outliers}` |
| method_used | VARCHAR(20) | ets / arima / prophet / lgbm / croston |
| selection_mode | VARCHAR(10) | `auto` / `manual` — lihat §6.8 |
| mase | NUMERIC, nullable | metrik akurasi utama |
| explanation | TEXT | penjelasan bahasa natural |
| forecast_data | JSONB | `[{date, value, lower, upper}]` |
| metrics | JSONB | `{avg_forecast, trend_direction, trend_pct, ...}` |
| created_at | TIMESTAMPTZ | |

### `reorder_recommendations`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| run_id | UUID FK → forecast_runs | |
| material_id | UUID FK → materials | |
| safety_stock | NUMERIC | |
| reorder_point | NUMERIC | |
| recommended_order_qty | NUMERIC | |
| status | VARCHAR(20) | urgent / safe / overstock |

### `overrides`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| target_type | VARCHAR(20) | `forecast_result` / `reorder_recommendation` |
| target_id | UUID | FK dinamis ke salah satu tabel di atas |
| user_id | UUID FK → users | siapa yang override |
| previous_value | JSONB | |
| new_value | JSONB | |
| reason | TEXT NOT NULL | wajib diisi — `OVERRIDE_REASON_REQUIRED` jika kosong |
| created_at | TIMESTAMPTZ | |

> Override **tidak menghapus** `forecast_results`/`reorder_recommendations` asli — hanya menambah entri baru di `overrides` sebagai revisi.

## 5. API Contract (`/api/v1`, merged)

```
POST   /api/v1/auth/login
GET    /api/v1/auth/me

GET    /api/v1/materials
POST   /api/v1/materials
PUT    /api/v1/materials/{id}
DELETE /api/v1/materials/{id}
POST   /api/v1/materials/import

POST   /api/v1/uploads                    # upload CSV historis konsumsi
GET    /api/v1/uploads/{session_id}
GET    /api/v1/uploads

POST   /api/v1/forecast/runs              # trigger forecast run (horizon, method opsional, dst)
GET    /api/v1/forecast/runs/{run_id}
GET    /api/v1/forecast/results?material_id=...

GET    /api/v1/reorder/recommendations
GET    /api/v1/reorder/recommendations/export?format=xlsx|pdf

POST   /api/v1/overrides                  # buat override baru
GET    /api/v1/overrides?target_id=...

GET    /api/v1/dashboard/summary
```

### Response Standard
```json
// Success
{ "success": true, "data": {}, "message": "string (optional)" }
// Error
{ "success": false, "error": { "code": "ERROR_CODE", "message": "Human readable" } }
```

### HTTP Status Code
200 berhasil · 201 resource dibuat · 400 validation error · 401 unauthorized · 403 forbidden · 404 not found · 422 invalid secara bisnis · 429 rate limit · 500 internal error · 503 dependency eksternal (Supabase/R2) unavailable

### Error Codes (merged, final)
```
AUTH_INVALID_CREDENTIALS     AUTH_TOKEN_EXPIRED           AUTH_EMAIL_NOT_VERIFIED
MATERIAL_NOT_FOUND           UPLOAD_INVALID_FORMAT        UPLOAD_FILE_TOO_LARGE
SESSION_NOT_FOUND            SESSION_EXPIRED               INSUFFICIENT_DATA
MODEL_SELECTION_FAILED       FORECAST_RUN_NOT_FOUND        BACKTEST_FAILED
OVERRIDE_REASON_REQUIRED     STORAGE_UPLOAD_FAILED          RATE_LIMIT_EXCEEDED
UNSUPPORTED_FORECAST_METHOD
```
> `UNSUPPORTED_FORECAST_METHOD` (400): dipakai saat user memilih metode manual (§6.8) yang namanya tidak terdaftar di registry atau tidak aktif di `FORECAST_ENGINES_ENABLED`.

## 6. Forecasting Engine — Auto Model Selection + Manual Override (Final)

> **v2.1 — ditambahkan atas permintaan user:** (1) user bisa memilih metode forecasting secara **manual sebelum generate**, sebagai alternatif dari Auto Model Selection; (2) setiap metode forecasting diimplementasikan sebagai **satu fungsi murni** (bukan class/Protocol) — lebih sederhana untuk ditulis, dites, dan dibaca satu-per-satu.

### 6.0 Kontrak Engine — Fungsional, 1 Fungsi per Metode

Setiap metode forecasting adalah **satu fungsi** dengan signature seragam, self-contained (melakukan backtest + fit + predict + explanation di dalam fungsi itu sendiri):

```python
# app/services/forecasting/types.py
@dataclass
class ForecastPoint:
    date: str
    value: float
    lower: float
    upper: float

@dataclass
class EngineResult:
    forecast: list[ForecastPoint]
    mase: float
    explanation: str

# Signature wajib untuk SETIAP metode — 1 file = 1 metode = 1 fungsi:
def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult: ...
```

Kenapa fungsi, bukan class: tidak ada state yang perlu disimpan antar pemanggilan (setiap forecast run selalu fit ulang dari data terbaru), jadi class + Protocol (`fit`/`predict`/`backtest` terpisah) hanya menambah boilerplate tanpa manfaat. Registry cukup berupa `dict[str, Callable]`, dan "factory" hanyalah lookup + validasi nama metode.

### 6.1 Pipeline (`forecast_service.py`) — Auto vs Manual

```python
def run_forecast_for_material(df: pd.DataFrame, horizon: int, requested_method: str | None = None) -> ForecastResultRecord:
    if len(df) < settings.BACKTEST_MIN_PERIODS:
        return ForecastResultRecord(status="INSUFFICIENT_DATA")

    profile = classification.classify(df)   # ADI, CV², kuadran — tetap dihitung untuk ditampilkan ke user,
                                              # walau mode manual dipakai (untuk konteks di UI)

    # ── MODE MANUAL: user sudah memilih metode sebelum generate ──
    if requested_method is not None:
        if requested_method not in registry.get_enabled_methods():
            raise UnsupportedForecastMethodError(requested_method)
        forecast_fn = registry.MODEL_REGISTRY[requested_method]
        try:
            result = forecast_fn(df, horizon)   # 1 fungsi, langsung dipakai — tidak ada fallback diam-diam
        except Exception as exc:
            return ForecastResultRecord(status="MODEL_SELECTION_FAILED", error=str(exc))
        return ForecastResultRecord(
            status="COMPLETED", method_used=requested_method, selection_mode="manual",
            profile=profile, **result.__dict__,
        )

    # ── MODE OTOMATIS: Auto Model Selection Engine ──
    candidates = registry.filter_candidates(profile)             # engine yang cocok kuadran & terdaftar aktif
    if not candidates:
        return ForecastResultRecord(status="MODEL_SELECTION_FAILED")

    scored = []
    for method_name in candidates:
        forecast_fn = registry.MODEL_REGISTRY[method_name]
        try:
            result = forecast_fn(df, horizon)                    # fungsi ini sudah menghitung MASE sendiri
            guardrail_penalty = scoring_engine.guardrail_check(df, result)
            score = scoring_engine.compute_score(result.mase, guardrail_penalty, profile, method_name)
            scored.append((method_name, score, result))
        except Exception:
            log.warning(f"{method_name} gagal saat backtest/fit, dikecualikan")

    if not scored:
        return ForecastResultRecord(status="MODEL_SELECTION_FAILED")

    scored.sort(key=lambda x: x[1], reverse=True)
    method_name, score, result = scored[0]                       # skor tertinggi menang (fungsi sudah berhasil dipanggil)
    return ForecastResultRecord(
        status="COMPLETED", method_used=method_name, selection_mode="auto",
        profile=profile, **result.__dict__,
    )
```

> Catatan: pada mode otomatis, kandidat yang **gagal** langsung dikecualikan di loop scoring (tidak masuk `scored`), jadi tidak perlu langkah "coba lagi sesuai urutan skor" terpisah — kandidat yang berhasil di-backtest sudah otomatis yang dipertimbangkan. Pada mode manual, kegagalan **tidak** di-fallback ke metode lain (lihat FR-3.11 di `PRD.md`) — user sudah memilih sadar, jadi errornya harus jelas, bukan diam-diam diganti.

### 6.2 Klasifikasi Demand (`classification.py`)
```python
@dataclass
class DemandProfile:
    n_points: int
    adi: float              # Average Demand Interval
    cv2: float               # Coefficient of Variation squared
    demand_class: str        # smooth / erratic / intermittent / lumpy
    has_seasonality: bool
    is_stationary: bool
    missing_ratio: float
    has_outliers: bool

def classify(df: pd.DataFrame) -> DemandProfile:
    adi = compute_adi(df)
    cv2 = compute_cv2(df)
    # Kuadran Syntetos-Boylan:
    #   ADI < 1.32 & CV² < 0.49  → smooth
    #   ADI < 1.32 & CV² >= 0.49 → erratic
    #   ADI >= 1.32 & CV² < 0.49 → intermittent
    #   ADI >= 1.32 & CV² >= 0.49 → lumpy
    demand_class = syntetos_boylan_quadrant(adi, cv2)
    ...
```

### 6.3 Filter Kandidat Engine per Kuadran (mode otomatis) / Daftar Pilihan (mode manual)
| Kuadran | Engine kandidat (auto) |
|---|---|
| smooth | ets, arima |
| erratic | lgbm, croston |
| intermittent | **croston**, arima (jika data cukup) |
| lumpy | **croston** |

> `prophet` belum diimplementasikan (lihat §6.6) — dikecualikan dari `quadrant_map` sampai fungsinya benar-benar ada, supaya auto-selection tidak pernah mencoba memanggil fungsi yang belum ditulis.

Untuk **mode manual**, user boleh memilih metode apa saja yang statusnya "tersedia" (ada di `MODEL_REGISTRY` dan aktif di `FORECAST_ENGINES_ENABLED`) — tidak dibatasi oleh kuadran. Ini disengaja: kalau planner secara sadar ingin coba ARIMA untuk item yang terklasifikasi `lumpy`, sistem tetap mengizinkan (hasilnya mungkin kurang akurat, tapi itu keputusan sadar planner, bukan bug).

### 6.4 Weighted Scoring (`scoring_engine.py`) — hanya dipakai mode otomatis
```python
def compute_score(mase: float, guardrail_penalty: float, profile: DemandProfile, method_name: str) -> float:
    fit_score = quadrant_fit_score(method_name, profile.demand_class)  # 0-1
    mase_score = 1 / (1 + mase)                                        # normalisasi, makin kecil MASE makin tinggi skor
    return (
        settings.SCORING_WEIGHT_MASE * mase_score +
        settings.SCORING_WEIGHT_GUARDRAIL * (1 - guardrail_penalty) +
        settings.SCORING_WEIGHT_FIT * fit_score
    )
```
> Mode manual **skip** fungsi ini sepenuhnya (lihat §6.1) — scoring hanya relevan untuk memilih otomatis di antara beberapa kandidat.

### 6.5 Registry — `dict[str, Callable]`, Bukan Class Registry
```python
# registry.py
from app.services.forecasting.engines.ets_engine import forecast_ets
from app.services.forecasting.engines.arima_engine import forecast_arima
from app.services.forecasting.engines.lightgbm_engine import forecast_lightgbm
from app.services.forecasting.engines.croston_engine import forecast_croston
# from app.services.forecasting.engines.prophet_engine import forecast_prophet  # TODO: belum diimplementasikan

MODEL_REGISTRY: dict[str, Callable[[pd.DataFrame, int], EngineResult]] = {
    "ets": forecast_ets,
    "arima": forecast_arima,
    "lgbm": forecast_lightgbm,
    "croston": forecast_croston,
    # "prophet": forecast_prophet,
}

def get_enabled_methods() -> set[str]:
    enabled = set(settings.FORECAST_ENGINES_ENABLED.split(","))
    return enabled & MODEL_REGISTRY.keys()   # abaikan nama di env yang belum ada fungsinya

def filter_candidates(profile: DemandProfile) -> list[str]:
    quadrant_map = {
        "smooth": ["ets", "arima"],
        "erratic": ["lgbm", "croston"],
        "intermittent": ["croston", "arima"],
        "lumpy": ["croston"],
    }
    return [m for m in quadrant_map[profile.demand_class] if m in get_enabled_methods()]
```
> Tidak ada `factory.py` terpisah lagi — karena engine adalah fungsi murni (stateless), "instansiasi" tidak diperlukan. Lookup nama → fungsi sudah cukup lewat `MODEL_REGISTRY` di atas. Kalau ada AI coding assistant lain yang masih mengacu ke `factory.py` dari draft lama, itu sudah tidak berlaku — lihat §6.0.

### 6.6 Kontrak 1-Fungsi-1-Metode (`engines/*.py`)
```python
# Setiap file di engines/ berisi TEPAT SATU fungsi publik dengan signature ini:
def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult:
    """
    df: kolom wajib `date` (datetime-like) dan `quantity` (numeric), sudah diurutkan per tanggal.
    horizon: jumlah periode ke depan yang diminta.
    Mengembalikan EngineResult(forecast, mase, explanation) — lihat §6.0.
    Fungsi ini SELF-CONTAINED: melakukan holdout backtest (untuk menghitung MASE),
    lalu fit ulang di seluruh data, lalu predict `horizon` ke depan — semua di dalam
    fungsi yang sama, tidak ada state yang dibagi ke fungsi lain.
    """
```
Status implementasi per metode (lihat `engines/README.md` untuk detail):

| Metode | File | Status |
|---|---|---|
| ETS (Exponential Smoothing) | `ets_engine.py` | ✅ Implemented |
| ARIMA | `arima_engine.py` | ✅ Implemented |
| Croston/SBA | `croston_engine.py` | ✅ Implemented |
| LightGBM | `lightgbm_engine.py` | ✅ Implemented |
| Prophet | `prophet_engine.py` | ⏳ TODO — butuh dependency berat (cmdstan build), ditunda sampai benar-benar dibutuhkan |

> Lihat `engines/README.md` (wajib dibaca sebelum menambah/ubah engine) untuk detail kontrak & cara registrasi.

### 6.7 Environment Variables
```env
FORECAST_ENGINES_ENABLED=ets,arima,lgbm,croston
SCORING_WEIGHT_MASE=0.6
SCORING_WEIGHT_GUARDRAIL=0.3
SCORING_WEIGHT_FIT=0.1
BACKTEST_MIN_PERIODS=12
ENGINE_TIMEOUT_SECONDS=45
FORECAST_TIMEOUT_SECONDS=120

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
MAX_UPLOAD_SIZE_MB=10
```

### 6.8 Request Contract — Manual Method Selection

`POST /api/v1/forecast/runs` menerima field `method` opsional:

```json
{
  "material_ids": ["<uuid>", "..."],
  "horizon": 30,
  "horizon_unit": "days",
  "method": null
}
```

- `method: null` (atau field tidak dikirim) → **mode otomatis**, Auto Model Selection Engine yang memilih (§6.1).
- `method: "arima"` (salah satu key di `MODEL_REGISTRY` yang aktif) → **mode manual**, seluruh material di run ini dipaksa pakai metode tsb.
- `method` diisi nama yang tidak dikenal/tidak aktif → `400 UNSUPPORTED_FORECAST_METHOD`.

`forecast_results` menyimpan `selection_mode` (`"auto"` atau `"manual"`) di kolom `data_profile`/kolom baru, supaya dashboard bisa menampilkan badge berbeda ("Dipilih otomatis" vs "Dipilih manual oleh user") — lihat komponen `MethodBadge.tsx` di frontend.

## 7. Storage Flow — Cloudflare R2

```
forecastiq-bucket/
├── temp/
│   └── uploads/{session_id}/{filename}.csv          ← TTL 1 jam sebelum divalidasi
└── permanent/
    ├── datasets/{user_id}/{session_id}/raw.csv       ← dataset asli setelah divalidasi
    ├── forecasts/{user_id}/{run_id}.json
    ├── exports/{user_id}/{run_id}/export.xlsx
    └── overrides/{user_id}/{override_id}.json
```
Cron cleanup setiap 30 menit menghapus `temp/` yang sudah lewat `expires_at`.

## 8. Error Handling

- Model gagal fit saat backtest → exclude, lanjut ke kandidat skor berikutnya.
- Semua kandidat gagal → `MODEL_SELECTION_FAILED`, `forecast_results.status` untuk item tsb ditandai gagal (run lain tetap lanjut).
- Data < `BACKTEST_MIN_PERIODS` → `INSUFFICIENT_DATA`, fail fast sebelum backtest.
- Timeout per-engine (`ENGINE_TIMEOUT_SECONDS`) — bukan timeout global, agar 1 item lambat tidak memblokir seluruh run.
- Tidak ada stack trace / detail internal yang di-expose ke client; semua di-log server-side.

## 9. Testing & Coverage (ringkas — detail penuh di `AGENTS.md` §3)

| Layer | Minimum Coverage |
|---|---|
| Endpoints (routes) | 90% |
| Services (business logic) | 85% |
| Forecasting engine module | 85% (mock/fixture data) |
| Storage service | 80% (mock R2) |
| Database models | 70% |

## 10. Rencana Deployment

- Dev: `docker-compose` (backend, frontend, postgres lokal untuk testing).
- Backend → Railway, Frontend → Vercel, DB/Auth → Supabase, Storage → Cloudflare R2 (sesuai keputusan di dokumen sumber).
- CI: lint + test + coverage gate sebelum merge (GitHub Actions).

---
*Lihat `RECONCILIATION.md` untuk daftar lengkap keputusan yang diambil saat menggabungkan spesifikasi AGENTS.md dan Notion Tech Docs.*
