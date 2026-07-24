# Rekonsiliasi: AGENTS.md vs Notion Tech Docs — ForecastIQ

Dokumen ini mencatat titik-titik konflik yang ditemukan antara **AGENTS.md** yang dikirim user dan halaman Notion **"Technical Documentation — ForecastIQ"**, keputusan final yang diambil, dan alasannya. Tujuannya agar `PRD.md`, `ARCHITECTURE.md`, `AGENTS.md`, dan `TASK_BREAKDOWN.md` final tidak saling kontradiksi.

> Konteks penting: user mengonfirmasi tujuan ForecastIQ **sama dengan** project "raw material/inventory forecasting PPIC" yang sudah dirintis sebelumnya — jadi resolusi di bawah selalu condong ke pendekatan yang paling cocok untuk domain **konsumsi raw material** (sering intermittent/sporadis), bukan domain generic sales/retail forecasting.

## Tabel Konflik & Resolusi

| # | Topik | AGENTS.md | Notion Tech Docs | **Keputusan Final** | Alasan |
|---|---|---|---|---|---|
| 1 | Model selection | ADI/CV² → kuadran Syntetos-Boylan (smooth/erratic/intermittent/lumpy), MASE, weighted scoring via env | Scoring poin sederhana (n_points, seasonality, stationarity) | **Pakai pendekatan AGENTS.md (ADI/CV²/MASE)** | Konsumsi raw material sering intermittent/lumpy (bukan demand harian yang mulus seperti retail). Syntetos-Boylan adalah metode standar industri untuk klasifikasi demand seperti ini. MASE juga lebih valid dari MAPE saat ada periode dengan konsumsi nol. |
| 2 | Struktur service | `app/services/forecasting/` (forecast_service, classification, scoring_engine, registry, factory, engines/) | `app/core/` (parser, analyzer, selector, forecaster) + `app/models/` | **Pakai struktur AGENTS.md** | Lebih eksplisit memisahkan classification & scoring sebagai module sendiri — dibutuhkan untuk pendekatan ADI/CV² yang dipilih di atas. |
| 3 | Data model upload | `upload_sessions` + `project_id` (multi-project) | `uploads` (per user langsung, tanpa konsep project) | **Pakai `upload_sessions`, tanpa `project_id` di MVP** | Konsep "project" belum perlu untuk internal tool 1 perusahaan; disederhanakan dulu, bisa ditambah kalau nanti benar E2 multi-tenant SaaS. Ditandai sebagai keputusan terbuka di bawah. |
| 4 | Grouping job forecast | Tidak eksplisit disebut "job", lebih ke "run" | `forecast_jobs` dengan polling status | **Pakai `forecast_runs`** (gabungan istilah) dengan status PENDING/PROCESSING/COMPLETED/FAILED ala Notion, tapi struktur hasil per-material ala kebutuhan PPIC (1 run bisa mencakup banyak material sekaligus) | PPIC upload 1 file berisi banyak SKU/material sekaligus — beda dari asumsi Notion (1 file = 1 time series). Jadi 1 `forecast_run` menghasilkan banyak `forecast_results` (satu per material). |
| 5 | Master data material | Tidak dibahas eksplisit | Tidak dibahas eksplisit | **Tetap ada `materials`** (dari PRD sebelumnya: code, unit, lead_time, MOQ, safety stock manual) | Ini yang membedakan ForecastIQ-untuk-PPIC dari generic sales forecasting tool — reorder point & safety stock butuh lead time & MOQ per item. |
| 6 | Reorder & Safety Stock | Tidak dibahas (AGENTS.md fokus ke model selection & override) | Tidak dibahas | **Tetap ada `reorder_recommendations`** (dari PRD sebelumnya) | Ini core value untuk PPIC — forecast saja tidak actionable tanpa rekomendasi reorder. |
| 7 | Planner override & audit trail | Wajib, non-negotiable, dengan `OVERRIDE_REASON_REQUIRED` | Tidak dibahas sama sekali | **Pakai aturan AGENTS.md — wajib ada** | Sangat relevan untuk adopsi PPIC: planner harus bisa override rekomendasi sistem dengan alasan tercatat (untuk audit & kepercayaan). |
| 8 | Error codes | SESSION_EXPIRED, OVERRIDE_REASON_REQUIRED, MODEL_SELECTION_FAILED, PROJECT_NOT_FOUND, dst | UPLOAD_INVALID_FORMAT, JOB_NOT_FOUND, FORECAST_ENGINE_FAILED, dst | **Gabungan keduanya** — lihat daftar final di `ARCHITECTURE.md` §API Contract | Tidak ada konflik nyata di sini, hanya union dari dua daftar; `PROJECT_NOT_FOUND` dihapus karena konsep project tidak dipakai (lihat #3). |
| 9 | Storage flow R2 | `temp/` + `permanent/` (datasets, forecasts, exports, overrides), TTL 1 jam | `uploads/` + `exports/` saja, TTL 24 jam | **Pakai struktur AGENTS.md (temp/permanent + folder overrides), TTL 1 jam** | Lebih lengkap — permanent dataset raw CSV penting untuk audit trail PPIC, dan folder khusus overrides selaras dengan keputusan #7. |
| 10 | Auth | JWT + Supabase disebut di env, tidak detail | Supabase Auth eksplisit | **Supabase Auth + JWT** (keduanya konsisten, Supabase Auth issue JWT) | Tidak ada konflik nyata — union. |
| 11 | Fallback model saat gagal | Exclude engine gagal, lanjut ke kandidat lain; semua gagal → `MODEL_SELECTION_FAILED` | Fallback chain eksplisit: prophet → ets → arima | **Gabung**: coba kandidat sesuai urutan skor (bukan urutan hardcode prophet→ets→arima), exclude yang gagal, lanjut ke skor berikutnya; semua gagal → `MODEL_SELECTION_FAILED` | Urutan berbasis skor lebih konsisten dengan prinsip "weighted scoring, bukan if-else rigid" di AGENTS.md §5. |
| 12 | Error code untuk RBAC forbidden (403) | Daftar error code final tidak punya kode "forbidden" generik | — | **Tambah `AUTH_FORBIDDEN` (403)** — dipakai saat role user tidak diizinkan akses resource (FR-8.2) | AGENTS.md §3 mewajibkan test case "Forbidden → 403", tapi daftar error code §4 belum menyediakan kode untuk itu. Ditambahkan di Fase 1 lewat jalur resmi (AGENTS.md §4 + ARCHITECTURE.md §5) sesuai larangan §13, bukan reuse `AUTH_INVALID_CREDENTIALS` yang menyesatkan. |

## ⚠️ Temuan Penting: Gap Engine untuk Demand Intermittent/Lumpy

AGENTS.md menyebutkan aturan: *"pola intermittent/lumpy mengecualikan smoothing method standar tanpa dukungan intermittent"* — tapi baik AGENTS.md maupun Notion Tech Docs **hanya mendaftarkan 4 engine: ETS, Prophet, ARIMA, LightGBM**. Tidak satupun dari keempatnya didesain untuk demand intermittent/lumpy (yang justru paling umum terjadi pada konsumsi raw material — item yang jarang dipakai tapi kritikal).

**Konsekuensi jika dibiarkan:** untuk material dengan pola intermittent/lumpy (kemungkinan besar mayoritas raw material di PPIC), tahap "filter engine kandidat" akan mengecualikan semua 4 engine yang ada → tidak ada kandidat tersisa → `MODEL_SELECTION_FAILED` untuk hampir semua item yang justru paling butuh forecast akurat.

**Rekomendasi (ditambahkan ke arsitektur final):** tambah engine ke-5: `croston_engine.py` — implementasi **Croston's Method** atau **SBA (Syntetos-Boylan Approximation)**, metode standar industri khusus untuk intermittent demand forecasting. Engine ini otomatis terdaftar di `registry.py` tanpa mengubah orchestrator (`forecast_service.py`), sesuai prinsip Registry/Factory pattern yang sudah disepakati.

## Keputusan Terbuka (Perlu Konfirmasi User — Tidak Blocking, Bisa Didiskusikan Kapan Saja)

1. **Multi-tenant/"project" konsep** — MVP ini diasumsikan untuk 1 perusahaan (semua user share 1 pool material). Kalau nanti mau dijual sebagai SaaS ke banyak perusahaan, perlu ditambah `organization_id`/`project_id`. Tidak urgent untuk MVP.
2. **Update Notion Tech Docs** — halaman Notion sekarang sudah tidak sinkron dengan keputusan final ini. Saya belum mengubahnya (belum diminta). Kalau mau, saya bisa update halaman Notion tersebut supaya konsisten dengan dokumen final di project ini.
3. **Croston/SBA engine** — ditambahkan sebagai rekomendasi teknis saya. Kalau ada preferensi lain untuk menangani intermittent demand (mis. TSB method), beri tahu saya.

---
*Dokumen ini adalah working note, bukan bagian dari deliverable utama — tapi disimpan agar keputusan tidak hilang/terulang tanya lagi di masa depan.*
