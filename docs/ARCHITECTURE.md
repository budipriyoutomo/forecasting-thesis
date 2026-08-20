# Dokumen Arsitektur Teknis
## ForecastIQ — ML Forecasting, Inventory Decision & Warehouse Capacity Constraint (Produk Minuman RTD)

| | |
|---|---|
| **Versi** | 3.0 (pivot — implementasi metodologi Thesis Noviana Asmoro, lihat `RECONCILIATION.md`) |
| **Tanggal** | 25 Juli 2026 |
| **Terkait** | `PRD.md`, `AGENTS.md` (instruksi coding), `RECONCILIATION.md` |

---

## 1. Ringkasan Arsitektur

```
┌─────────────────────┐        HTTPS/REST (/api/v1)     ┌──────────────────────┐
│  Frontend (Next.js)  │ <──────────────────────────────> │  Backend (FastAPI)   │
│  VPS (Docker+Caddy)   │                                  │  VPS (Docker)         │
└─────────────────────┘                                  └──────────┬───────────┘
                                                                     │
                                    ┌────────────────────────────────┼─────────────────────────┐
                                    │                                │                         │
                          ┌─────────▼─────────┐          ┌───────────▼──────────┐   ┌───────────▼─────────┐
                          │ PostgreSQL (VPS/Supabase)│    │ Object Storage (S3)   │   │ Supabase Auth (JWT) │
                          │ products, materials,  │       │ temp/ + permanent/    │   │                     │
                          │ boms, forecast_runs/   │       │ CSV & export files    │   │                     │
                          │ results, reorder,      │       └───────────────────────┘   └─────────────────────┘
                          │ warehouse_config,      │
                          │ overrides              │
                          └───────────────────────┘
```

### Prinsip Arsitektur

- **Stateless backend** — semua state di database, tidak ada session di memory server.
- **Synchronous untuk MVP** — forecasting dijalankan sync; Celery/Redis ditambahkan hanya jika ada sinyal kebutuhan nyata (training LSTM untuk banyak SKU sekaligus bisa jadi trigger ini).
- **Registry pattern untuk model engine** — tambah engine baru = tambah fungsi + daftar di registry, tanpa ubah orchestrator/endpoint/test.
- **Orkestrasi terpusat** — semua proses forecasting wajib melalui `forecast_service.py`, tidak boleh inline di router.
- **Comparative selection, bukan classification** — beda dengan v2.0 (ADI/CV² → kuadran), v3.0 membandingkan seluruh metode aktif langsung via backtest dan memilih akurasi terbaik (selaras Bab III thesis).
- **BOM sebagai jembatan produk jadi → material** — semua modul downstream (buffer stock, kebutuhan material, validasi kapasitas gudang) mengonsumsi hasil forecast produk jadi melalui `bom_service.py`.
- **Data & Model Integrity** — data historis asli & hasil forecast/override tidak pernah di-overwrite secara silent.
- **TDD sebagai workflow wajib** — lihat `AGENTS.md` §3.

## 2. Tech Stack

| Layer | Teknologi | Hosting |
|---|---|---|
| Frontend | Next.js (App Router) + TypeScript + Tailwind v3 + shadcn/ui (Radix) + TanStack Query + TanStack Table v8 + Recharts + next-themes | VPS (Docker, di balik Caddy) |
| Backend | FastAPI (Python 3.11+) + Pydantic v2 + SQLAlchemy 2.0 async | VPS (Docker, di balik Caddy) |
| Database | PostgreSQL | VPS (Docker) — atau Supabase, cukup ganti `DATABASE_URL` |
| Object Storage | S3-compatible via boto3 (CSV upload & export) | IDCloudHost Object Storage |
| Auth | Supabase Auth (JWT) | Supabase |
| Forecasting — konvensional | pandas/numpy (Moving Average, Exponential Smoothing — implementasi manual sesuai rumus Bab III thesis, bukan statsmodels) | Backend (bundled) |
| Forecasting — ML | scikit-learn (`RandomForestRegressor`), `xgboost` (`XGBRegressor`), TensorFlow/Keras (`LSTM`) | Backend (bundled) |
| Forecasting — nonaktif default | statsmodels (ETS/ARIMA), Prophet, LightGBM, Croston/SBA custom — dipertahankan di registry, lihat §6.9 | Backend (bundled, tidak dipanggil default) |
| Testing | pytest + pytest-cov (backend), Vitest + RTL (frontend) | CI |

> **Catatan performa:** training LSTM (TensorFlow) jauh lebih berat dari Moving Average/ES. Pastikan `ENGINE_TIMEOUT_SECONDS` berbeda per kategori metode (lihat §6.8) dan pertimbangkan menjalankan training di process terpisah/worker jika volume SKU besar (lihat §Non-Functional di `PRD.md`).

## 3. Struktur Folder (Monorepo)

```
forecastiq/
├── AGENTS.md                        ← Instruksi wajib untuk AI coding assistant (final)
├── README.md
├── docs/
│   ├── PRD.md
│   ├── ARCHITECTURE.md              ← dokumen ini
│   ├── DEPLOYMENT.md                ← runbook deployment VPS (langkah demi langkah)
│   ├── TASK_BREAKDOWN.md
│   └── RECONCILIATION.md
│
├── frontend/                        ← Next.js
│   ├── src/
│   │   ├── app/
│   │   │   ├── (auth)/login/  register/
│   │   │   ├── (dashboard)/
│   │   │   │   ├── dashboard/
│   │   │   │   ├── products/           ← master data produk jadi
│   │   │   │   ├── materials/          ← master data material/packaging
│   │   │   │   ├── boms/               ← CRUD Bill of Materials
│   │   │   │   ├── warehouse/          ← konfigurasi kapasitas gudang
│   │   │   │   ├── forecast/new/       ← upload + konfigurasi
│   │   │   │   ├── forecast/[id]/      ← hasil forecast per run (termasuk breakdown BOM & validasi gudang)
│   │   │   │   └── settings/
│   │   │   └── layout.tsx
│   │   ├── components/
│   │   │   ├── ui/                     ← primitif shadcn/ui (hasil generate CLI, jangan tulis tangan)
│   │   │   ├── common/                 ← primitif lintas fitur: DataTable, PageHeader, EmptyState,
│   │   │   │                              TableSkeleton, FormError, ConfirmDialog
│   │   │   ├── layout/                 ← AppSidebar, AppHeader, Breadcrumbs, ThemeToggle, SkipLink
│   │   │   ├── providers/              ← QueryProvider, ThemeProvider
│   │   │   ├── auth/
│   │   │   ├── upload/
│   │   │   ├── config/
│   │   │   ├── forecast/
│   │   │   ├── products/
│   │   │   ├── materials/
│   │   │   ├── boms/                   ← visual breakdown produk → material
│   │   │   ├── warehouse/              ← indikator validasi kapasitas
│   │   │   ├── override/
│   │   │   └── dashboard/
│   │   ├── lib/{api.ts, auth.ts, download.ts, format.ts, navigation.ts, utils.ts}
│   │   │      ← navigation.ts = sumber tunggal struktur nav (dipakai sidebar + breadcrumb)
│   │   │        format.ts = formatter angka/persen/uang/tanggal terpusat (Decimal backend = string)
│   │   ├── hooks/{useAuth, useProducts, useMaterials, useBoms, useUploads, useForecast,
│   │   │          useReorder, useWarehouse, useOverrides, useMetrics, useDashboard,
│   │   │          useExport, use-mobile}
│   │   └── types/
│   ├── components.json                 ← konfigurasi shadcn/ui (style new-york, baseColor slate)
│   ├── tailwind.config.ts
│   ├── vitest.config.ts + vitest.setup.ts   ← setup men-stub matchMedia/ResizeObserver/pointer
│   │                                          capture yang tidak ada di jsdom tapi dipakai Radix
│   └── package.json
│
├── backend/                          ← FastAPI
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/v1/
│   │   │   ├── auth.py
│   │   │   ├── products.py
│   │   │   ├── materials.py
│   │   │   ├── boms.py
│   │   │   ├── uploads.py
│   │   │   ├── forecast.py
│   │   │   ├── reorder.py
│   │   │   ├── warehouse.py
│   │   │   └── overrides.py
│   │   ├── services/
│   │   │   ├── forecasting/
│   │   │   │   ├── forecast_service.py     ← orkestrasi (satu-satunya entry point)
│   │   │   │   ├── evaluation.py           ← hitung MAD/MFE/MSE/MAPE (+ MASE opsional), pilih metode terbaik
│   │   │   │   ├── registry.py             ← MODEL_REGISTRY
│   │   │   │   ├── types.py                ← ForecastPoint, EngineResult
│   │   │   │   └── engines/
│   │   │   │       ├── README.md           ← kontrak base_engine, cara tambah engine baru
│   │   │   │       ├── moving_average_engine.py
│   │   │   │       ├── exponential_smoothing_engine.py
│   │   │   │       ├── random_forest_engine.py
│   │   │   │       ├── xgboost_engine.py
│   │   │   │       ├── lstm_engine.py
│   │   │   │       └── legacy/             ← dinonaktifkan default, lihat §6.9
│   │   │   │           ├── ets_engine.py
│   │   │   │           ├── arima_engine.py
│   │   │   │           ├── lightgbm_engine.py
│   │   │   │           ├── croston_engine.py
│   │   │   │           └── prophet_engine.py   ← TODO, belum diimplementasikan
│   │   │   ├── data_ingestion_service.py   ← parsing & validasi CSV (Forecast/Planning/Actual)
│   │   │   ├── bom_service.py              ← breakdown kebutuhan material dari forecast produk jadi
│   │   │   ├── reorder_service.py          ← safety stock, buffer stock, reorder point, EOQ dinamis
│   │   │   ├── warehouse_service.py        ← kapasitas gudang & validasi muat/tidak
│   │   │   ├── cost_service.py             ← TIC (Ordering Cost + Holding Cost), % penghematan
│   │   │   ├── inventory_metrics_service.py ← service level, fill rate, stock out rate, inventory turnover
│   │   │   ├── override_service.py
│   │   │   ├── storage_service.py          ← object storage S3-compatible
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

## 4. Data Model (Final — v3.0)

### `users`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| email | VARCHAR(255) UNIQUE | |
| name | VARCHAR(100) | |
| role | VARCHAR(20) | admin / ppic / purchasing / viewer |
| is_verified | BOOLEAN | default false |
| created_at / updated_at | TIMESTAMPTZ | |

### `products` (baru — produk jadi, objek forecasting utama)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| code | VARCHAR unique | kode SKU, mis. `KBYPL 200` — unik, `PRODUCT_CODE_EXISTS` jika duplikat saat create/import |
| name | VARCHAR | mis. "KIN Yogurt Original 200ml" |
| category | VARCHAR | mis. "RTD Yogurt" |
| unit | VARCHAR | UOM, mis. "PCS" |
| created_at / updated_at | TIMESTAMPTZ | |

### `materials`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| code | VARCHAR unique | kode material/packaging — unik, `MATERIAL_CODE_EXISTS` jika duplikat saat create/import |
| name | VARCHAR | |
| category | VARCHAR | |
| unit | VARCHAR | satuan |
| lead_time_days | INTEGER | |
| moq | NUMERIC | minimum order quantity |
| dimension | JSONB | `{length, width, height}` — dipakai untuk kalkulasi kapasitas gudang §6.7 |
| qty_per_pallet | NUMERIC | jumlah unit material per palet |
| manual_safety_stock | NUMERIC, nullable | override manual |
| created_at / updated_at | TIMESTAMPTZ | |

### `boms` (baru — Bill of Materials)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| product_id | UUID FK → products | |
| material_id | UUID FK → materials | |
| qty_per_unit | NUMERIC | jumlah material dibutuhkan per 1 unit produk jadi |
| created_at / updated_at | TIMESTAMPTZ | |

> Satu `product` bisa punya banyak baris `boms` (banyak komponen material). Dipakai oleh `bom_service.py` untuk breakdown forecast produk → kebutuhan material, dan untuk hitung Standar Pemakaian Material (buffer stock, FR-4.2).

### `upload_sessions`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| user_id | UUID FK → users | |
| file_name | VARCHAR | |
| file_url | TEXT | URL di object storage (temp atau permanent) |
| file_size_kb | INTEGER | |
| n_rows | INTEGER | |
| n_products_detected | INTEGER | |
| preview_data | JSONB | 5 baris pertama |
| warnings | JSONB, nullable | |
| status | VARCHAR(20) | pending / validated / failed / expired |
| created_at | TIMESTAMPTZ | |
| expires_at | TIMESTAMPTZ | created_at + 1 jam (jika belum divalidasi) |

### `demand_history` (revisi dari `consumption_history` v2.0 — 3 seri paralel)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| product_id | UUID FK → products, **nullable** | null bila produk sumber sudah dihapus/di-rename setelah histori diupload — pola sama seperti `consumption_history.material_id` di v2.0 |
| product_code | VARCHAR | snapshot kode produk saat upload — fallback tampilan/laporan bila `product_id` null |
| period | DATE | biasanya awal bulan |
| forecast_existing | NUMERIC, nullable | angka forecast metode existing perusahaan (moving average manual) — dipakai sebagai baseline pembanding akurasi |
| planning | NUMERIC, nullable | rencana produksi aktual (setelah judgment planner) |
| actual | NUMERIC | realisasi produksi/penjualan — ini yang jadi target/label untuk training model ML |
| upload_session_id | UUID FK → upload_sessions | |

> Struktur 3-kolom ini (`forecast_existing`/`planning`/`actual`) mengikuti data riil di `Simulasi Thesis.xlsx` sheet "Bab I Plan vs Forecast" — dibutuhkan agar dashboard bisa menghitung gap akurasi ForecastIQ vs kondisi existing (FR-9.1/9.2 di `PRD.md`). Pola `product_id` nullable + `product_code` snapshot mengikuti keputusan git v2.0 (`RECONCILIATION.md` #14) — histori tidak boleh hilang/putus hanya karena master data produk berubah/dihapus.

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

> Satu `forecast_run` mencakup **banyak produk sekaligus** (bukan 1 run = 1 SKU).

### `forecast_results`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| run_id | UUID FK → forecast_runs | |
| product_id | UUID FK → products | |
| method_used | VARCHAR(30) | moving_average / exponential_smoothing / random_forest / xgboost / lstm |
| selection_mode | VARCHAR(10) | `auto` (comparative) / `manual` |
| candidates_evaluated | JSONB | `[{method, mad, mfe, mse, mape}]` — hasil semua metode yang diuji, untuk transparansi & explanation |
| mad / mfe / mse / mape | NUMERIC, nullable | metrik akurasi metode terpilih |
| mase | NUMERIC, nullable | metrik tambahan opsional (lihat `RECONCILIATION.md` Keputusan Terbuka v3.0 poin 3), tidak ditampilkan default di UI thesis |
| explanation | TEXT | penjelasan bahasa natural |
| forecast_data | JSONB | `[{date, value, lower, upper}]` |
| metrics | JSONB | `{avg_forecast, trend_direction, trend_pct, gap_vs_existing_pct, ...}` |
| created_at | TIMESTAMPTZ | |

### `material_requirements` (baru — hasil breakdown BOM per run)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| run_id | UUID FK → forecast_runs | |
| material_id | UUID FK → materials | |
| forecast_qty | NUMERIC | total kebutuhan material hasil breakdown BOM dari seluruh produk terkait |
| standard_usage_qty | NUMERIC, nullable | Output Produksi Aktual × BOM (dipakai untuk buffer stock) |
| actual_usage_qty | NUMERIC, nullable | pemakaian aktual material (dari input/upload aktual) |
| buffer_stock_pct | NUMERIC, nullable | (standard_usage − actual_usage)/standard_usage × 100 |
| created_at | TIMESTAMPTZ | |

### `reorder_recommendations`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| run_id | UUID FK → forecast_runs | |
| material_id | UUID FK → materials | |
| safety_stock | NUMERIC | SS = Z × STD × √L |
| buffer_stock | NUMERIC | dari `material_requirements.buffer_stock_pct` |
| reorder_point | NUMERIC | |
| eoq_qty | NUMERIC | hasil EOQ dinamis, dibulatkan ke kelipatan MOQ |
| ordering_cost | NUMERIC | biaya pesan yang dipakai di perhitungan EOQ |
| holding_cost | NUMERIC | biaya simpan per unit per periode |
| total_inventory_cost | NUMERIC | TIC = Ordering Cost + Holding Cost |
| status | VARCHAR(20) | urgent / safe / overstock |

> `current_stock` **bukan** kolom persisten di tabel ini — dikirim sebagai parameter request saat `POST /api/v1/reorder/recommendations` (lihat §5), karena stok aktual berubah-ubah dan sumber kebenarannya ada di luar ForecastIQ (belum ada integrasi ERP/WMS di MVP, lihat `PRD.md` §Out-of-scope).

### `warehouse_config` (baru)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| category | VARCHAR | kategori material yang di-cover (mis. "packaging") |
| warehouse_area_m2 | NUMERIC | luas gudang |
| pallet_dimension | JSONB | `{length, width, height}` |
| updated_at | TIMESTAMPTZ | |

### `warehouse_validations` (baru — hasil validasi per run)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| run_id | UUID FK → forecast_runs | |
| total_pallet_capacity | NUMERIC | Luas Gudang ÷ Dimensi Palet |
| total_pallet_required | NUMERIC | dihitung dari total rekomendasi inventory ÷ qty per pallet, seluruh material |
| is_within_capacity | BOOLEAN | |
| created_at | TIMESTAMPTZ | |

### `inventory_metrics` (baru — per run, per produk/material)
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| run_id | UUID FK → forecast_runs | |
| target_type | VARCHAR(20) | `product` / `material` |
| target_id | UUID | |
| scope | VARCHAR(20) | `baseline` (actual vs planning existing) / `forecastiq` (actual vs forecast ForecastIQ) — memisahkan kinerja EXISTING dari ForecastIQ (RECONCILIATION §Fase 7) |
| service_level | NUMERIC | 1 − stock_out_rate |
| fill_rate | NUMERIC | 1 − Σ kekurangan / Σ demand |
| stock_out_rate | NUMERIC | proporsi periode kekurangan |
| inventory_turnover | NUMERIC | Σ demand ÷ persediaan rata-rata |

### `overrides`
| Kolom | Tipe | Keterangan |
|---|---|---|
| id | UUID | PK |
| target_type | VARCHAR(20) | `forecast_result` / `material_requirement` / `reorder_recommendation` |
| target_id | UUID | FK dinamis ke salah satu tabel di atas — `OVERRIDE_TARGET_NOT_FOUND` jika `target_id` tidak ditemukan di tabel yang dirujuk `target_type` |
| user_id | UUID FK → users | siapa yang override |
| previous_value | JSONB | |
| new_value | JSONB | |
| reason | TEXT NOT NULL | wajib diisi — `OVERRIDE_REASON_REQUIRED` jika kosong |
| created_at | TIMESTAMPTZ | |

> Override **tidak menghapus** data asli — hanya menambah entri baru di `overrides` sebagai revisi.

## 5. API Contract (`/api/v1`, v3.0)

```
POST   /api/v1/auth/login
GET    /api/v1/auth/me

GET    /api/v1/products
POST   /api/v1/products
PUT    /api/v1/products/{id}
DELETE /api/v1/products/{id}
POST   /api/v1/products/import

GET    /api/v1/materials
POST   /api/v1/materials
PUT    /api/v1/materials/{id}
DELETE /api/v1/materials/{id}
POST   /api/v1/materials/import

GET    /api/v1/boms?product_id=...
POST   /api/v1/boms
PUT    /api/v1/boms/{id}
DELETE /api/v1/boms/{id}
POST   /api/v1/boms/import

POST   /api/v1/uploads                    # upload Forecast/Planning/Actual historis
GET    /api/v1/uploads/{session_id}
GET    /api/v1/uploads

POST   /api/v1/forecast/runs              # trigger forecast run (horizon, method opsional)
GET    /api/v1/forecast/runs/{run_id}
GET    /api/v1/forecast/results?product_id=...

GET    /api/v1/forecast/runs/{run_id}/material-requirements   # breakdown BOM

POST   /api/v1/reorder/recommendations    # generate & persist rekomendasi (body: run_id, current_stock per material — lihat catatan di §4 `reorder_recommendations`)
GET    /api/v1/reorder/recommendations
GET    /api/v1/reorder/recommendations/export?format=xlsx|pdf

GET    /api/v1/warehouse/config
PUT    /api/v1/warehouse/config
GET    /api/v1/forecast/runs/{run_id}/warehouse-validation

GET    /api/v1/forecast/runs/{run_id}/inventory-metrics
GET    /api/v1/forecast/runs/{run_id}/cost-summary          # TIC & % penghematan

POST   /api/v1/overrides
GET    /api/v1/overrides?target_id=...

GET    /api/v1/dashboard/summary
```

> **Pola `POST` sebelum `GET` untuk resource yang di-generate** (bukan sekadar CRUD): `reorder_recommendations` di-generate dari hasil forecast + BOM + `current_stock` request-time, jadi wajib ada `POST` yang menghitung & menyimpan, baru `GET` yang memfilter/menampilkan hasil tersimpan. Ikuti pola yang sama bila menambah resource turunan baru di masa depan — lihat `AGENTS.md` §11.

### Response Standard

```json
// Success
{ "success": true, "data": {}, "message": "string (optional)" }
// Error
{ "success": false, "error": { "code": "ERROR_CODE", "message": "Human readable" } }
```

### HTTP Status Code

200 berhasil · 201 resource dibuat · 400 validation error · 401 unauthorized · 403 forbidden · 404 not found · 422 invalid secara bisnis · 429 rate limit · 500 internal error · 503 dependency eksternal (Supabase/object storage) unavailable

### Error Codes (v3.1, final — merge dengan implementasi git aktual)

```
AUTH_INVALID_CREDENTIALS     AUTH_TOKEN_EXPIRED           AUTH_EMAIL_NOT_VERIFIED
AUTH_FORBIDDEN                PRODUCT_CODE_EXISTS          MATERIAL_CODE_EXISTS
PRODUCT_NOT_FOUND            MATERIAL_NOT_FOUND           BOM_NOT_FOUND
UPLOAD_INVALID_FORMAT        UPLOAD_FILE_TOO_LARGE
SESSION_NOT_FOUND            SESSION_EXPIRED               INSUFFICIENT_DATA
MODEL_SELECTION_FAILED       FORECAST_RUN_NOT_FOUND         BACKTEST_FAILED
UNSUPPORTED_FORECAST_METHOD  WAREHOUSE_CONFIG_NOT_FOUND     WAREHOUSE_CAPACITY_EXCEEDED
OVERRIDE_REASON_REQUIRED     OVERRIDE_TARGET_NOT_FOUND      STORAGE_UPLOAD_FAILED
RATE_LIMIT_EXCEEDED
```

> `WAREHOUSE_CAPACITY_EXCEEDED` bukan hard-block (400) melainkan flag di response 200 (`warehouse_validations.is_within_capacity = false`) — keputusan akhir tetap di tangan planner via override, sesuai FR-6.4 di `PRD.md`. `BOM_NOT_FOUND` dipakai saat breakdown material diminta tapi produk belum punya BOM terdaftar. `AUTH_FORBIDDEN` (403) dipakai saat user terautentikasi tapi tidak berhak atas resource yang diminta (beda dengan `AUTH_INVALID_CREDENTIALS`/`AUTH_TOKEN_EXPIRED` yang 401). `PRODUCT_CODE_EXISTS`/`MATERIAL_CODE_EXISTS` dipakai saat `code` duplikat pada create/import produk atau material. `OVERRIDE_TARGET_NOT_FOUND` dipakai saat `target_id` pada `POST /api/v1/overrides` tidak ditemukan di tabel yang dirujuk `target_type`. Empat code ini diwarisi dari implementasi v2.0 di git (lihat `RECONCILIATION.md` §"Rekonsiliasi v3.1").

## 6. Forecasting Engine — Comparative Selection (Final v3.0)

> **Perubahan mendasar dari v2.0:** tidak ada lagi klasifikasi pola demand (ADI/CV² → kuadran Syntetos-Boylan). v3.0 mengikuti Bab III thesis: jalankan seluruh metode aktif, uji akurasinya, pilih yang terbaik. Lihat `RECONCILIATION.md` §"Rekonsiliasi v3.0" untuk alasan.

### 6.0 Kontrak Engine — Fungsional, 1 Fungsi per Metode (tidak berubah dari v2.0)

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
    mad: float
    mfe: float
    mse: float
    mape: float
    explanation: str

# Signature wajib untuk SETIAP metode — 1 file = 1 metode = 1 fungsi:
def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult: ...
```

Fungsi itu sendiri melakukan **holdout backtest** (hitung MAD/MFE/MSE/MAPE dari data yang di-hold out), fit ulang di seluruh data, lalu predict `horizon` ke depan — self-contained, satu fungsi, satu file. Tidak ada class/Protocol (alasan sama seperti v2.0: setiap forecast run selalu fit ulang dari data terbaru, tidak ada state yang perlu disimpan).

### 6.1 Pipeline (`forecast_service.py`) — Comparative Auto vs Manual

```python
def run_forecast_for_product(df: pd.DataFrame, horizon: int, requested_method: str | None = None) -> ForecastResultRecord:
    min_periods = settings.LSTM_MIN_PERIODS if requested_method == "lstm" else settings.BACKTEST_MIN_PERIODS
    if len(df) < min_periods:
        return ForecastResultRecord(status="INSUFFICIENT_DATA")

    # ── MODE MANUAL: user sudah memilih metode sebelum generate ──
    if requested_method is not None:
        if requested_method not in registry.get_enabled_methods():
            raise UnsupportedForecastMethodError(requested_method)
        forecast_fn = registry.MODEL_REGISTRY[requested_method]
        try:
            result = forecast_fn(df, horizon)
        except Exception as exc:
            return ForecastResultRecord(status="MODEL_SELECTION_FAILED", error=str(exc))
        return ForecastResultRecord(
            status="COMPLETED", method_used=requested_method, selection_mode="manual",
            **result.__dict__,
        )

    # ── MODE OTOMATIS: Comparative Selection (bandingkan semua metode aktif) ──
    candidates_evaluated = []
    for method_name in registry.get_enabled_methods():
        forecast_fn = registry.MODEL_REGISTRY[method_name]
        try:
            result = forecast_fn(df, horizon)              # fungsi ini sudah menghitung MAD/MFE/MSE/MAPE sendiri
            candidates_evaluated.append((method_name, result))
        except Exception:
            log.warning(f"{method_name} gagal saat backtest/fit, dikecualikan")

    if not candidates_evaluated:
        return ForecastResultRecord(status="MODEL_SELECTION_FAILED")

    # Pilih berdasarkan metrik primer yang dikonfigurasi (default: MAPE, terendah menang)
    ranking_metric = settings.FORECAST_RANKING_METRIC  # "mape" | "mad" | "mse" | "mfe_abs"
    method_name, result = min(candidates_evaluated, key=lambda x: getattr(x[1], ranking_metric))
    return ForecastResultRecord(
        status="COMPLETED", method_used=method_name, selection_mode="auto",
        candidates_evaluated=[{"method": m, **r.__dict__} for m, r in candidates_evaluated],
        **result.__dict__,
    )
```

> Kegagalan satu metode **tidak** menggagalkan seluruh proses perbandingan (exclude & lanjut). Mode manual **tidak** fallback ke metode lain bila gagal (user sudah memilih sadar) — sama seperti aturan v2.0.

### 6.2 Metrik Evaluasi (`evaluation.py`)

```python
def mad(actual: np.ndarray, forecast: np.ndarray) -> float:
    return np.mean(np.abs(actual - forecast))

def mfe(actual: np.ndarray, forecast: np.ndarray) -> float:
    return np.mean(actual - forecast)   # bias: positif = under-forecast, negatif = over-forecast

def mse(actual: np.ndarray, forecast: np.ndarray) -> float:
    return np.mean((actual - forecast) ** 2)

def mape(actual: np.ndarray, forecast: np.ndarray) -> float:
    # guard divide-by-zero untuk periode actual = 0 (tetap bisa terjadi meski objek utama produk jadi)
    mask = actual != 0
    return np.mean(np.abs((actual[mask] - forecast[mask]) / actual[mask])) * 100
```

> `mase()` tetap disediakan sebagai fungsi tambahan opsional (dipakai bila `settings.COMPUTE_MASE = true`) untuk kebutuhan produk non-thesis (lihat `RECONCILIATION.md` Keputusan Terbuka v3.0 poin 3), tapi **tidak** dipakai untuk ranking default.

### 6.3 Registry — `dict[str, Callable]`

```python
# registry.py
from app.services.forecasting.engines.moving_average_engine import forecast_moving_average
from app.services.forecasting.engines.exponential_smoothing_engine import forecast_exponential_smoothing
from app.services.forecasting.engines.random_forest_engine import forecast_random_forest
from app.services.forecasting.engines.xgboost_engine import forecast_xgboost
from app.services.forecasting.engines.lstm_engine import forecast_lstm
# Legacy (nonaktif default, lihat §6.9):
# from app.services.forecasting.engines.legacy.ets_engine import forecast_ets
# from app.services.forecasting.engines.legacy.arima_engine import forecast_arima
# from app.services.forecasting.engines.legacy.lightgbm_engine import forecast_lightgbm
# from app.services.forecasting.engines.legacy.croston_engine import forecast_croston

MODEL_REGISTRY: dict[str, Callable[[pd.DataFrame, int], EngineResult]] = {
    "moving_average": forecast_moving_average,
    "exponential_smoothing": forecast_exponential_smoothing,
    "random_forest": forecast_random_forest,
    "xgboost": forecast_xgboost,
    "lstm": forecast_lstm,
    # "ets": forecast_ets,             # nonaktif default
    # "arima": forecast_arima,         # nonaktif default
    # "lgbm": forecast_lightgbm,       # nonaktif default
    # "croston": forecast_croston,     # nonaktif default
}

def get_enabled_methods() -> set[str]:
    enabled = set(settings.FORECAST_ENGINES_ENABLED.split(","))
    return enabled & MODEL_REGISTRY.keys()
```

### 6.4 Kontrak per Metode (`engines/*.py`)

| Metode | File | Ringkasan Implementasi (lihat Bab III thesis untuk detail rumus) |
|---|---|---|
| Moving Average | `moving_average_engine.py` | Fₜ₊₁ = rata-rata n periode terakhir; n dikonfigurasi (`MOVING_AVERAGE_WINDOW`, default 3) |
| Exponential Smoothing | `exponential_smoothing_engine.py` | Fₜ₊₁ = αDₜ + (1−α)Fₜ; α di-tuning dengan grid 0,1–0,9 saat backtest, pilih α dengan MAPE terendah |
| Random Forest | `random_forest_engine.py` | `RandomForestRegressor(n_estimators=100, max_depth=10)`, fitur: lag_1, lag_7 (bila data cukup), bulan, hari |
| XGBoost | `xgboost_engine.py` | `XGBRegressor`, fitur: lag_1/7/30 + kalender (tahun, bulan, hari, minggu ISO), hyperparameter tuning via `GridSearchCV` (n_estimators, max_depth, learning_rate) |
| LSTM | `lstm_engine.py` | Min-Max scaling, sequence window 12 periode, arsitektur 2× `LSTM(units=50)` + `Dense(1)`, optimizer Adam, loss MSE, `epochs=100, batch_size=32` |

Setiap fungsi **self-contained**: melakukan holdout backtest (untuk MAD/MFE/MSE/MAPE), fit ulang di seluruh data, predict `horizon` ke depan, dan generate `explanation` — semua dalam satu fungsi.

### 6.5 Environment Variables

```env
FORECAST_ENGINES_ENABLED=moving_average,exponential_smoothing,random_forest,xgboost,lstm
FORECAST_RANKING_METRIC=mape          # mape | mad | mse | mfe_abs
COMPUTE_MASE=true                     # hitung & simpan MASE tambahan (tidak dipakai ranking)
BACKTEST_MIN_PERIODS=12
LSTM_MIN_PERIODS=24
MOVING_AVERAGE_WINDOW=3
ENGINE_TIMEOUT_SECONDS=45             # konvensional & tree-based
LSTM_ENGINE_TIMEOUT_SECONDS=120       # LSTM butuh timeout lebih longgar
FORECAST_TIMEOUT_SECONDS=180

DATABASE_URL=postgresql://...
SUPABASE_URL=...
SUPABASE_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
S3_ENDPOINT_URL=https://is3.cloudhost.id
S3_ACCESS_KEY=...
S3_SECRET_KEY=...
S3_REGION=SouthJkt-a
S3_BUCKET_NAME=forecastiq-bucket
S3_ADDRESSING_STYLE=auto      # auto | path | virtual
JWT_SECRET_KEY=...
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
MAX_UPLOAD_SIZE_MB=10

# Dev login lokal (tanpa Supabase Auth) — hanya berlaku saat ENVIRONMENT=development.
# Di environment lain flag ini diabaikan; verifikasi kredensial tetap ke Supabase Auth.
# Akun demo per role dibuat oleh `python -m app.scripts.seed_dev_users`.
DEV_AUTH_ENABLED=false
DEV_AUTH_PASSWORD=demo1234

# EOQ & Cost
DEFAULT_ORDERING_COST=...
DEFAULT_HOLDING_COST_RATE=...

# Warehouse
WAREHOUSE_PALLET_NO_RACKING=true      # sesuai batasan masalah thesis
```

### 6.6 Request Contract — Manual Method Selection

`POST /api/v1/forecast/runs`:

```json
{
  "product_ids": ["<uuid>", "..."],
  "horizon": 30,
  "horizon_unit": "days",
  "method": null
}
```

- `method: null` → **mode otomatis**, Comparative Selection membandingkan seluruh metode aktif (§6.1).
- `method: "xgboost"` (salah satu key aktif di `MODEL_REGISTRY`) → **mode manual**, seluruh produk di run ini dipaksa pakai metode tsb.
- `method` tidak dikenal/tidak aktif → `400 UNSUPPORTED_FORECAST_METHOD`.

### 6.7 Kalkulasi Kapasitas Gudang (`warehouse_service.py`)

```python
def compute_pallet_capacity(warehouse_area_m2: float, pallet_dimension: dict) -> int:
    pallet_footprint = pallet_dimension["length"] * pallet_dimension["width"]
    return int(warehouse_area_m2 // pallet_footprint)

def compute_material_capacity(pallet_capacity: int, qty_per_pallet: float) -> float:
    return pallet_capacity * qty_per_pallet

def validate_capacity(recommendations: list[ReorderRecommendation], materials: dict) -> WarehouseValidation:
    total_pallet_required = sum(
        (r.safety_stock + r.buffer_stock + r.eoq_qty) / materials[r.material_id].qty_per_pallet
        for r in recommendations
    )
    pallet_capacity = compute_pallet_capacity(...)
    return WarehouseValidation(
        total_pallet_capacity=pallet_capacity,
        total_pallet_required=total_pallet_required,
        is_within_capacity=total_pallet_required <= pallet_capacity,
    )
```

### 6.8 Kalkulasi EOQ Dinamis & Total Cost (`reorder_service.py`, `cost_service.py`)

```python
def compute_eoq(periods: list[InventoryPeriod], ordering_cost: float, holding_cost: float) -> EOQResult:
    # TC = nS + Σ(It x H) — n = jumlah pemesanan pada horizon, It = persediaan periode t
    total_cost_by_n = {
        n: n * ordering_cost + sum(period_inventory(n, t) * holding_cost for t in periods)
        for n in candidate_order_frequencies(periods)
    }
    best_n = min(total_cost_by_n, key=total_cost_by_n.get)
    eoq_qty = total_forecast_demand(periods) / best_n
    return EOQResult(n=best_n, eoq_qty=eoq_qty, total_cost=total_cost_by_n[best_n])

def round_to_moq(eoq_qty: float, moq: float) -> float:
    return math.ceil(eoq_qty / moq) * moq

def compute_savings_pct(tic_actual: float, tic_proposed: float) -> float:
    return (tic_actual - tic_proposed) / tic_actual * 100
```

### 6.9 Engine Legacy (Nonaktif Default — dari Arsitektur v2.0)

ETS, ARIMA, LightGBM, dan Croston/SBA **tidak dihapus** dari codebase — dipindah ke `engines/legacy/` dan tidak didaftarkan ke `MODEL_REGISTRY` aktif secara default (di-comment, lihat §6.3). Rasionalnya ada di `RECONCILIATION.md` §Keputusan Terbuka v3.0 poin 2: metode-metode ini (khususnya Croston untuk demand intermittent/lumpy) tetap relevan untuk kasus forecasting **raw material langsung** di luar konteks produk jadi RTD yang jadi objek thesis. Mengaktifkan kembali cukup uncomment import + tambah ke `FORECAST_ENGINES_ENABLED`, tanpa ubah `forecast_service.py`.

## 7. Storage Flow — Object Storage (S3-compatible)

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

**Provider-agnostic.** `storage_service.py` hanya memakai operasi S3 standar — `put_object`, `copy_object`, `delete_object` — tanpa presigned URL dan tanpa API khas vendor. Endpoint, region, kredensial, dan addressing style semuanya dibaca dari env (`S3_ENDPOINT_URL`, `S3_REGION`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_ADDRESSING_STYLE`), jadi pindah provider cukup ganti env tanpa menyentuh kode. Provider aktif: **IDCloudHost Object Storage** (`https://is3.cloudhost.id`, region `SouthJkt-a`) — lihat `RECONCILIATION.md` §Migrasi Object Storage untuk alasannya.

`S3_ADDRESSING_STYLE` dipakai kalau provider tidak punya wildcard DNS `{bucket}.{endpoint}`: set `path` supaya boto3 memakai `{endpoint}/{bucket}/{key}`. Signature dipatok `s3v4`.

## 8. Error Handling

- Satu metode forecasting gagal fit saat backtest → exclude, lanjut ke metode kandidat lain.
- Semua kandidat gagal → `MODEL_SELECTION_FAILED`, `forecast_results.status` untuk produk tsb ditandai gagal (run lain tetap lanjut).
- Data < `BACKTEST_MIN_PERIODS` (atau `LSTM_MIN_PERIODS` khusus LSTM) → `INSUFFICIENT_DATA`, fail fast sebelum backtest.
- Timeout per-engine (`ENGINE_TIMEOUT_SECONDS` / `LSTM_ENGINE_TIMEOUT_SECONDS`) — bukan timeout global.
- Produk tanpa BOM terdaftar saat breakdown material diminta → `BOM_NOT_FOUND` (bukan fatal — forecast produk tetap tersimpan, hanya breakdown material yang tidak tersedia).
- Rekomendasi melebihi kapasitas gudang → **bukan error**, ditandai `is_within_capacity = false` di response, planner tetap bisa lanjut dengan override.
- User terautentikasi tapi tidak berhak atas resource → `AUTH_FORBIDDEN` (403), bukan `404` (hindari kebocoran informasi keberadaan resource tetap dipertimbangkan per kasus).
- Kode (`code`) duplikat saat create/import produk atau material → `PRODUCT_CODE_EXISTS` / `MATERIAL_CODE_EXISTS` (400/422), bukan 500 dari constraint violation database yang bocor ke client.
- `target_id` override tidak ditemukan di tabel yang dirujuk `target_type` → `OVERRIDE_TARGET_NOT_FOUND` (404).
- Tidak ada stack trace / detail internal yang di-expose ke client; semua di-log server-side.

## 9. Testing & Coverage (ringkas — detail penuh di `AGENTS.md` §3)

| Layer | Minimum Coverage |
|---|---|
| Endpoints (routes) | 90% |
| Services (business logic) | 85% |
| Forecasting engine module (evaluation, registry, tiap engine) | 85% (mock/fixture data) |
| BOM/warehouse/EOQ/cost services | 85% — verifikasi manual hasil hitung dengan data contoh |
| Storage service | 80% (client S3 di-mock) |
| Database models | 70% |

## 10. Deployment — VPS Self-Hosted (Docker)

Target deployment dipindah dari Railway/Vercel ke **VPS self-hosted** (20 Agustus 2026, lihat `RECONCILIATION.md` §Deployment VPS). Storage → IDCloudHost, Auth → Supabase Auth, DB → Postgres di VPS yang sama (atau Supabase, tinggal ganti `DATABASE_URL`).

### Topologi

```
                    Internet
                       │  :80 / :443
              ┌───────▼───────┐
              │  Caddy         │  TLS otomatis (Let's Encrypt)
              │  (Caddyfile)   │  satu-satunya port yang terbuka ke publik
              └─┬───────────┬─┘
    /api/*, /health │         │  sisanya
              ┌────▼───┐   ┌───▼─────┐
              │ backend │   │ frontend │   jaringan internal compose,
              │  :8000  │   │  :3000   │   port TIDAK di-publish ke host
              └────┬───┘   └─────────┘
                   │
              ┌────▼────┐      ┌─────────────────┐
              │ postgres │      │ IDCloudHost S3   │ (eksternal)
              └──────────┘      └─────────────────┘
```

Frontend & backend berbagi satu domain → request API bersifat **same-origin**, jadi CORS tidak pernah jadi masalah di production.

### File

| File | Peran |
|---|---|
| `docker-compose.yml` | **dev saja** — bind mount + `--reload` + `npm run dev` |
| `docker-compose.prod.yml` | production — image di-build, port aplikasi tidak di-publish |
| `Caddyfile` | reverse proxy, TLS otomatis, security header |
| `.env.prod.example` | template seluruh konfigurasi server (salin → `.env.prod`, jangan di-commit) |
| `backend/Dockerfile` + `docker-entrypoint.sh` | non-root, healthcheck, `alembic upgrade head` saat start |
| `frontend/Dockerfile` | multi-stage → `output: "standalone"`, non-root |
| `backend/.dockerignore`, `frontend/.dockerignore` | mencegah `.env`, `.venv`, `node_modules` masuk image |

### Alur deploy

> Runbook langkah demi langkah (siapkan VPS, firewall, Docker, DNS, user admin pertama, backup, troubleshooting) ada di **`DEPLOYMENT.md`**. Ringkasnya:

```bash
cp .env.prod.example .env.prod && chmod 600 .env.prod   # lalu isi kredensial
make prod-up        # build + start; migrasi jalan otomatis di entrypoint
make prod-logs
make prod-deploy    # deploy ulang setelah git pull
```

Cron pembersih file temp (§7) dijadwalkan di crontab VPS:
`*/30 * * * * cd /path/ke/forecastiq && make prod-cleanup`

### Yang wajib diperhatikan

- **`NEXT_PUBLIC_*` di-inline saat build image**, bukan dibaca saat runtime. Mengubah nilainya di `.env.prod` tanpa `--build` tidak berpengaruh apa pun.
- **Migrasi jalan di entrypoint backend**, dan `set -e` membuat container gagal start kalau migrasi gagal — disengaja, supaya aplikasi tidak pernah hidup di atas skema yang salah. Bisa dimatikan lewat `RUN_MIGRATIONS=false`.
- **Firewall VPS**: buka 22, 80, 443 saja. Postgres tidak di-publish ke host oleh compose production.
- CI: lint + test + coverage gate sebelum merge (GitHub Actions) — belum ada deploy otomatis, deploy masih manual lewat SSH.
- **LSTM**: `tensorflow` masih di-comment di `requirements.txt`, jadi engine `lstm` di-exclude otomatis (§6.4). `.env.prod.example` sengaja tidak mencantumkan `lstm` di `FORECAST_ENGINES_ENABLED` supaya perilakunya eksplisit, bukan gagal diam-diam. Untuk mengaktifkan: uncomment `tensorflow>=2.16` (image Python 3.11 mendukung), perhatikan ukuran image (+±1 GB) dan waktu build.

---
*Lihat `RECONCILIATION.md` §"Rekonsiliasi v3.0" dan §"Rekonsiliasi v3.1" untuk daftar lengkap perubahan dari v2.0 dan alasannya.*