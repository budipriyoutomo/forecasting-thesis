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

## ⚠️ Temuan Penting: Gap Engine untuk Demand Intermittent/Lumpy

AGENTS.md menyebutkan aturan: *"pola intermittent/lumpy mengecualikan smoothing method standar tanpa dukungan intermittent"* — tapi baik AGENTS.md maupun Notion Tech Docs **hanya mendaftarkan 4 engine: ETS, Prophet, ARIMA, LightGBM**. Tidak satupun dari keempatnya didesain untuk demand intermittent/lumpy (yang justru paling umum terjadi pada konsumsi raw material — item yang jarang dipakai tapi kritikal).

**Konsekuensi jika dibiarkan:** untuk material dengan pola intermittent/lumpy (kemungkinan besar mayoritas raw material di PPIC), tahap "filter engine kandidat" akan mengecualikan semua 4 engine yang ada → tidak ada kandidat tersisa → `MODEL_SELECTION_FAILED` untuk hampir semua item yang justru paling butuh forecast akurat.

**Rekomendasi (ditambahkan ke arsitektur final):** tambah engine ke-5: `croston_engine.py` — implementasi **Croston's Method** atau **SBA (Syntetos-Boylan Approximation)**, metode standar industri khusus untuk intermittent demand forecasting. Engine ini otomatis terdaftar di `registry.py` tanpa mengubah orchestrator (`forecast_service.py`), sesuai prinsip Registry/Factory pattern yang sudah disepakati.

> **Status per v3.0 (lihat di bawah): approach ADI/CV²/Croston di atas SUPERSEDED.** Setelah dokumen ini ditulis, project pivot untuk mengimplementasikan metodologi thesis akademik (lihat Rekonsiliasi v3.0). Pendekatan klasifikasi kuadran demand & Croston/SBA **tidak dipakai lagi** di MVP — digantikan pendekatan komparatif (bandingkan semua metode via backtest, pilih akurasi terbaik) sesuai Bab III thesis. Bagian ini dipertahankan sebagai jejak historis keputusan v1–v2, bukan dihapus, sesuai prinsip "jejak keputusan harus tetap ada" (`AGENTS.md` larangan #13).

## Keputusan Terbuka (v1–v2, sudah dijawab sebagian di v3.0 — lihat catatan di tiap poin)

1. **Multi-tenant/"project" konsep** — MVP ini diasumsikan untuk 1 perusahaan (semua user share 1 pool material). Kalau nanti mau dijual sebagai SaaS ke banyak perusahaan, perlu ditambah `organization_id`/`project_id`. Tidak urgent untuk MVP. *(Masih terbuka di v3.0 — tidak berubah oleh pivot thesis.)*
2. **Update Notion Tech Docs** — halaman Notion sekarang sudah tidak sinkron dengan keputusan final ini. Belum diubah (belum diminta).
3. **Croston/SBA engine** — *(Superseded oleh v3.0 — lihat di bawah, engine ini tidak lagi bagian dari MVP.)*

---

## Rekonsiliasi v3.0 — Pivot ke Implementasi Thesis (25 Juli 2026)

### Konteks & Trigger

User meng-attach dua dokumen akademik ke project ini: **"Draft Thesis Noviana Asmoro - 202012320009.docx"** (judul: *Model Integrasi Machine Learning Forecasting dan Inventory Decision dengan Warehouse Capacity Constraint pada Produk Minuman RTD*) dan **"Simulasi Thesis.xlsx"** (workbook pendukung Bab I & Bab II thesis: data historis Forecast/Planning/Actual per SKU, tabel posisi penelitian, dan tabel literature review).

Setelah dibandingkan dengan `PRD.md`/`ARCHITECTURE.md`/`AGENTS.md` versi v2.0 (hasil rekonsiliasi AGENTS.md vs Notion), ditemukan beberapa perbedaan mendasar (lihat tabel di bawah). User secara eksplisit mengonfirmasi: **"Tool = implementasi thesis"** — artinya ForecastIQ harus dibangun mengikuti metodologi persis yang dipakai di thesis, bukan sekadar mengambil sebagian ide.

### Bukti dari `Simulasi Thesis.xlsx`

Sheet **"Bab II Posisi Penelitian"** (baris 8, row penelitian milik Noviana Asmoro sendiri) secara eksplisit mengonfirmasi kombinasi final:

- Objek kajian: **FMCG — kategori Beverage**
- Metode peramalan dipakai: **Exponential Smoothing ✓, Rata-rata Bergerak ✓, Random Forest ✓, LSTM ✓, XGBoost ✓** — sedangkan ARIMA, Holt-Winters, SVR, MLR, Decision Tree, Neural Network (generic), AdaBoost **tidak dipakai** (kosong/"-").
- Integrasi Persediaan: **Ya**
- Keterbatasan Kapasitas Gudang: **Ya**
- Optimasi Persediaan: **Ya**
- Optimasi Biaya: **Ya**
- Visualisasi Data (Power BI): **Tidak** (bukan variabel penelitian, tapi tidak menghalangi ForecastIQ tetap punya dashboard sebagai fitur produk, bukan bagian dari klaim ilmiah thesis).

Sheet **"Bab I Plan vs Forecast"** memuat struktur data riil perusahaan objek penelitian: per varian/SKU (mis. *KIN Yogurt Original 200ml*, kode `KBYPL 200`), dengan kolom **Forecast** (hasil metode existing perusahaan), **Planning** (rencana produksi aktual setelah judgment planner), **Actual** (realisasi produksi), per bulan, selama 2024–2025. Struktur 3-seri paralel ini (bukan cuma 1 kolom "actual konsumsi") penting untuk desain data model baru — lihat §Data Model v3.0 di `ARCHITECTURE.md`.

### Tabel Perubahan Utama (v2.0 → v3.0)

| Aspek | v2.0 (sebelumnya) | v3.0 (mengikuti thesis) | Alasan |
|---|---|---|---|
| Objek forecasting | Raw material langsung (forecasting demand produk jadi = Out of Scope MVP) | **Produk jadi (finished goods/SKU minuman RTD)** — raw material/packaging diturunkan via **BOM** (Bill of Materials) dari forecast produk jadi | Ini persis objek penelitian thesis: forecasting fokus ke produk minuman RTD botol, packaging material dihitung sebagai turunannya. Backward-calc via BOM naik status dari "Roadmap Post-MVP" jadi **MVP wajib**. |
| Metode forecasting | ETS, ARIMA, Prophet (TODO), LightGBM, Croston/SBA | **Moving Average, Exponential Smoothing (baseline konvensional)** + **Random Forest, XGBoost, LSTM (ML)** | Sesuai konfirmasi tabel Posisi Penelitian di atas. ARIMA/Prophet/LightGBM/Croston **dikeluarkan dari MVP** (bukan dihapus permanen — lihat "Keputusan Terbuka v3.0" di bawah). |
| Cara pilih metode ("Auto Model Selection") | Klasifikasi ADI/CV² → kuadran Syntetos-Boylan → filter kandidat per kuadran → weighted scoring (MASE + guardrail + fit) | **Comparative backtest**: jalankan ke-5 metode di atas untuk tiap SKU, hitung metrik akurasi, pilih metode dengan error terendah — tanpa klasifikasi kuadran demand | Ini pendekatan yang dipakai di Bab III thesis (bandingkan semua metode secara langsung via pengujian peramalan, bukan klasifikasi pola demand dulu). Prinsip "weighted scoring via config" tetap dipertahankan sebagai opsi (lihat Keputusan Terbuka), tapi default MVP mengikuti thesis apa adanya. |
| Metrik evaluasi forecast | MASE (dipilih khusus karena valid saat ada demand nol) | **MAD, MFE, MSE, MAPE** (4 metrik, sesuai Bab III thesis) | Harus match dengan metodologi pengujian yang akan dipertanggungjawabkan di thesis. MASE tetap disimpan sebagai metrik tambahan opsional (lihat Keputusan Terbuka #2) karena secara teknis lebih robust untuk data raw material yang intermittent. |
| Safety stock | SS = Z × STD × √L (rumus klasik, sudah ada) | **Sama** (SS = Z × STD × √L) — tidak berubah | Formula di v2.0 sudah identik dengan formula Bab III thesis. Tidak ada konflik. |
| Buffer stock | Tidak ada konsep ini | **Baru:** Buffer Stock = (Standar Pemakaian Material − Aktual Pemakaian Material) × 100%, di mana Standar Pemakaian = Output Produksi × BOM | Wajib ada di thesis untuk mengantisipasi waste produksi. Butuh data BOM (formulasi) dan output produksi aktual. |
| Reorder qty | Reorder point + qty pertimbangkan MOQ (tanpa EOQ) | **Tambah EOQ dinamis**: TC = nS + Σ(Iₜ × H), untuk menentukan jumlah pesanan ekonomis, dikombinasikan dengan MOQ sebagai batas bawah | Salah satu tujuan penelitian eksplisit thesis: "menghasilkan model optimasi terintegrasi untuk meminimalkan total biaya persediaan dan biaya penyimpanan." |
| Warehouse capacity constraint | Tidak ada modul ini sama sekali | **Modul baru**: hitung kapasitas gudang berbasis palet (Jumlah palet = Luas Gudang ÷ Dimensi Palet; Kapasitas material = Jumlah palet × Qty material/palet), lalu validasi apakah rekomendasi inventory/EOQ result muat secara fisik di gudang | Ini bagian dari **judul thesis** — komponen paling khas dan tidak boleh hilang. |
| Evaluasi kinerja inventory | Tidak eksplisit dibahas di PRD v2.0 | **Baru, eksplisit:** Service Level, Fill Rate, Stock Out Rate, Inventory Turnover — semua dengan rumus dari Bab III thesis | Selaras dengan FR-6 dashboard v2.0, tapi sekarang formula & definisinya dikunci mengikuti thesis. |
| Total cost | Belum ada perhitungan total biaya eksplisit | **Baru:** TIC (Total Inventory Cost) = Ordering Cost + Holding Cost, dengan metrik keberhasilan tambahan "% penghematan" = (TIC aktual − TIC usulan) / TIC aktual × 100% | Tujuan penelitian #4 thesis: optimasi untuk meminimumkan total biaya. |
| Data historis | `consumption_history` — 1 seri (qty pemakaian) per material per tanggal | **Perlu diperluas** agar bisa menyimpan 3 seri paralel (Forecast eksisting perusahaan / Planning / Actual) per SKU per bulan, agar ForecastIQ bisa **membuktikan** peningkatan akurasi dibanding metode existing perusahaan (bagian dari success metric thesis) | Struktur data riil di `Simulasi Thesis.xlsx` sheet "Bab I Plan vs Forecast" memuat 3 kolom paralel ini, bukan cuma 1 kolom actual. |

### Yang TIDAK berubah (tetap dipertahankan dari v2.0)

- **Planner override & audit trail (FR-5)** — thesis tidak membahas ini sama sekali, tapi tidak bertentangan, dan ini fitur bernilai tinggi untuk adopsi PPIC riil. Diperlakukan sebagai **fitur produk tambahan ForecastIQ di luar klaim akademik thesis**, tetap wajib ada.
- **Dashboard & visualisasi (FR-6)** — thesis eksplisit menandai "Visualisasi Power BI: Tidak" sebagai variabel penelitian (karena bukan itu yang mereka uji), tapi itu tidak berarti ForecastIQ dilarang punya dashboard. Dashboard tetap ada sebagai kebutuhan produk.
- **Struktur `upload_sessions`, response standard, role-based access, storage flow R2** — tidak tersentuh oleh pivot ini, seluruhnya independen dari metodologi forecasting.
- Prinsip **1 fungsi murni per metode forecasting** (`forecast_<method>(df, horizon) -> EngineResult`), **Registry pattern**, **fail gracefully per item/per engine** — pola arsitektur ini dipertahankan, hanya isi `MODEL_REGISTRY`-nya yang berganti metode.

### Keputusan Terbuka v3.0 (perlu dikonfirmasi user — tidak blocking, tapi sebaiknya direview)

1. **Cakupan produk vs raw material**: v3.0 ini menjadikan forecasting produk jadi (SKU minuman RTD) sebagai objek utama, dengan raw material/packaging sebagai turunan BOM. Apakah ForecastIQ **tetap mempertahankan** kemampuan forecasting **langsung** atas raw material (tanpa BOM), untuk item yang datanya hanya tersedia di level bahan baku (bukan produk jadi)? Rekomendasi saya: **pertahankan keduanya** — endpoint forecast bisa jalan di level `product` (lalu di-breakdown via BOM) ATAU langsung di level `material` (kalau user tidak punya BOM lengkap) — supaya tool tetap berguna untuk kasus PPIC yang lebih umum, tidak hanya kasus 1 perusahaan di thesis.
2. **ARIMA/Prophet/LightGBM/Croston**: dikeluarkan dari daftar `FORECAST_ENGINES_ENABLED` default MVP, tapi kode/kontrak engine sebelumnya tidak dihapus dari referensi arsitektur — cukup dinonaktifkan via env var, sesuai prinsip "tambah/kurang metode tanpa ubah kode" yang sudah disepakati. Jika suatu saat produk dijual ke banyak perusahaan (bukan cuma 1 case study), engine-engine ini kemungkinan besar akan dipakai ulang untuk item raw material yang polanya intermittent (Croston tetap metode standar industri terbaik untuk itu) — Confirm: setuju didiamkan nonaktif (bukan dihapus total) di v3.0?
3. **MASE vs MAD/MFE/MSE/MAPE**: default MVP memakai 4 metrik thesis untuk keperluan validasi akademik. Apakah MASE tetap dihitung & disimpan sebagai metrik tambahan (tidak ditampilkan ke thesis, tapi berguna secara produk saat nanti dipakai multi-perusahaan dengan item intermittent)? Rekomendasi saya: ya, hitung & simpan semua metrik (MAD/MFE/MSE/MAPE/MASE), tampilkan MAD/MFE/MSE/MAPE sebagai default di UI/laporan thesis.
4. **Multi-tenant/"project" konsep** — pertanyaan lama dari v1–v2, masih belum urgent, tidak berubah oleh pivot ini.

---

## Rekonsiliasi v3.1 — Merge dengan Kode & Dokumen GitHub Aktual (25 Juli 2026)

### Konteks & Trigger

User meminta dokumen v3.0 dicek dan dicocokkan dengan dokumen di repo GitHub tersambung (`budipriyoutomo/forecasting-thesis`, sync source project ini). Ternyata `claude/*.md` yang jadi basis penulisan v3.0 **sudah tertinggal (stale)** dari repo asli — repo GitHub sudah berkembang lebih jauh dengan 6 keputusan tambahan (lahir dari proses implementasi nyata) yang tidak pernah disinkronkan balik ke project ini.

**Temuan yang jauh lebih penting:** repo GitHub bukan cuma dokumen — di sana sudah ada **kode backend lengkap dan teruji** untuk **Fase 0–8** dari `TASK_BREAKDOWN.md` versi lama (v2.0, arsitektur raw material + ADI/CV² + ETS/ARIMA/LightGBM/Croston), semuanya ditandai selesai dengan coverage ~95%:

- Fase 0 (monorepo setup, CI) ✅
- Fase 1 (auth Supabase JWT + RBAC `require_role`) ✅
- Fase 2 (CRUD master data material + import CSV) ✅
- Fase 3 (upload/ingestion, `storage_service` R2 temp→permanent, cron cleanup) ✅
- Fase 4 (Auto Model Selection Engine — `classification.py` ADI/CV², `ets_engine.py`/`arima_engine.py`/`lightgbm_engine.py`/`croston_engine.py`, `registry.py`, `forecast_service.py` mode auto & manual) ✅
- Fase 5 (`reorder_service.compute_reorder` — safety stock, reorder point, order qty, status urgent/safe/overstock) ✅
- Fase 6 (`override_service` — append-only, audit trail, `OVERRIDE_TARGET_NOT_FOUND`) ✅
- Fase 7 (dashboard — `dashboard_service`, `ForecastChart`, `ExplanationBox`) ✅
- Fase 8 (export Excel/PDF — `export_service`, builder fungsi murni) ✅
- Fase 9 (hardening/E2E/deployment) — **belum**.

User dikonfirmasi (via pertanyaan eksplisit di sesi ini): kode existing ini **dimigrasi/direfactor** menuju arsitektur v3.0 (implementasi thesis), bukan dibiarkan terpisah dan bukan didiamkan sampai keputusan lanjutan. Lihat §"Rencana Migrasi v3.1" di `TASK_BREAKDOWN.md` untuk detail per-fase.

### 6 Keputusan Implementasi dari GitHub (RECONCILIATION #12–17 versi repo) — Digabungkan ke v3.1

Keputusan ini lahir dari proses coding nyata (bukan dari draft dokumen), dan **semuanya tetap berlaku di v3.1** karena sifatnya generik (bukan spesifik ke metodologi ADI/CV² v2.0 yang sudah superseded):

| # | Keputusan | Tetap berlaku di v3.1? | Catatan |
|---|---|---|---|
| 12 | `AUTH_FORBIDDEN` (403) — role tidak diizinkan akses resource | ✅ Ya | Generik RBAC, tidak terkait metodologi forecasting. |
| 13 | `MATERIAL_CODE_EXISTS` (409) — konflik keunikan kode saat create/import | ✅ Ya, diperluas | Berlaku juga untuk `products.code` (entitas baru v3.0) — ditambah error code baru senada, lihat di bawah. |
| 14 | `consumption_history.material_id` dibuat nullable + kolom `material_code` (mengatasi kode di file upload yang belum terdaftar di master data) | ✅ Ya, pola dipertahankan | Di v3.1, `demand_history.product_id` mengikuti pola sama: nullable + kolom `product_code`, agar upload tidak ditolak total hanya karena SKU belum terdaftar. |
| 15 | Kolom `status` di `forecast_results` (COMPLETED/INSUFFICIENT_DATA/MODEL_SELECTION_FAILED per-item) | ✅ Ya | Tetap dibutuhkan di v3.1 — kegagalan 1 produk tidak boleh menggagalkan run (AGENTS.md §5). |
| 16 | `POST /reorder/recommendations` (generate+persist) + `current_stock` sebagai **input request**, bukan kolom tabel | ✅ Ya | Pola yang sama dipakai untuk endpoint EOQ/warehouse-validation baru di v3.1 — generate dulu via POST, baru bisa di-GET. |
| 17 | `OVERRIDE_TARGET_NOT_FOUND` (404) — target override polimorfik tidak ditemukan | ✅ Ya | Berlaku juga untuk target baru v3.1 (`material_requirement`). |

**Error code tambahan baru di v3.1** (mengikuti pola #13 di atas, supaya konsisten): `PRODUCT_CODE_EXISTS` (409) — konflik keunikan `products.code`. Ditambahkan di sini dulu sebelum dipakai di kode, sesuai larangan §13 AGENTS.md.

Daftar error code final v3.1 (union dari v3.0 + 6 keputusan git + 1 tambahan baru) — lihat `ARCHITECTURE.md` §5 dan `AGENTS.md` §4 untuk daftar lengkap yang sudah diperbarui.

### Implikasi ke Dokumen Lain (sudah diterapkan)

- **`ARCHITECTURE.md`**: daftar error codes final ditambah `AUTH_FORBIDDEN`, `MATERIAL_CODE_EXISTS`, `PRODUCT_CODE_EXISTS`, `OVERRIDE_TARGET_NOT_FOUND`; tabel `demand_history` menyertakan catatan pola `product_id` nullable + `product_code`; tabel `forecast_results` menyertakan kolom `status`; endpoint reorder ditulis sebagai `POST` (generate) + `GET` (filter), dengan `current_stock` sebagai parameter request.
- **`AGENTS.md`**: daftar error code final §4 diperbarui; checklist PR §11 ditambah item terkait pola `*_code` unik dan `POST` sebelum `GET` untuk resource yang di-generate.
- **`TASK_BREAKDOWN.md`**: ditulis ulang total sebagai **rencana migrasi** dari kode v2.0 existing menuju v3.0 — bukan daftar fase greenfield. Lihat dokumen tsb untuk urutan migrasi per-fase (apa yang dipertahankan, diganti, atau net-new).

### Batasan Diketahui: Akses Tulis ke GitHub

Sesi ini **tidak punya GitHub connector tersambung** (dicek via `ListConnectors` — kosong; dicari di marketplace via `SearchMcpRegistry` — tidak ditemukan konektor GitHub yang bisa langsung dipasang). Artinya saya belum bisa membuka PR langsung ke `budipriyoutomo/forecasting-thesis`. User diminta untuk memeriksa **Settings → Connectors** di claude.ai untuk opsi GitHub (kalau tersedia di organisasi/plan-nya) dan mengaktifkannya untuk chat ini; sementara itu dokumen final tetap disimpan di project ini dan dikirim sebagai file agar bisa di-commit manual.

---

## Fase Migrasi 7 — Total Biaya & Evaluasi Kinerja Inventory (26 Juli 2026)

### Konteks
Fase Migrasi 7 (net-new) mengimplementasikan `cost_service.py`, `inventory_metrics_service.py`, model `inventory_metrics`, dan endpoint `GET /forecast/runs/{run_id}/cost-summary` + `GET /forecast/runs/{run_id}/inventory-metrics`. Rumus TIC & % penghematan sudah baku di `ARCHITECTURE.md` §6.8; rumus 4 metrik kinerja inventory (service level, fill rate, stock out rate, inventory turnover) **tidak** dispesifikasikan di doc maupun ditemukan di `Simulasi Thesis.xlsx` (hanya disebut nama di sheet "Bab II Penelitian Terdahulu"). Keputusan di bawah diambil bersama user (26 Juli 2026) agar bisa dipertanggungjawabkan di thesis.

### Keputusan
1. **`cost_service.py` tidak menduplikasi rumus.** `compute_tic`, `compute_savings_pct`, `compute_eoq` sudah ada di `reorder_service.py` (sisa Fase 5) — `cost_service.py` meng-*import* & mengorkestrasi, bukan menyalin (hindari dua sumber kebenaran rumus). `CostService.get_cost_summary` mengagregasi TIC usulan dari `reorder_recommendations` tersimpan (ForecastIQ) dan menghitung TIC baseline dari seri **planning** perusahaan (planning → BOM breakdown → EOQ per material, simetris dengan jalur forecast), lalu `savings_pct = (TIC_baseline − TIC_usulan) / TIC_baseline × 100`.
2. **Rumus 4 metrik kinerja inventory** (fungsi murni, diverifikasi manual, AGENTS.md §3), atas dua deret selaras `demand`/`supply` per periode:
   - `shortage_t = max(0, demand_t − supply_t)`
   - `fill_rate = 1 − Σshortage_t / Σdemand_t` (β, berbasis unit)
   - `stock_out_rate = jumlah periode(shortage_t > 0) / T`
   - `service_level = 1 − stock_out_rate` (α, berbasis siklus/periode)
   - `inventory_turnover = Σdemand_t / rata-rata(supply_t)` (throughput ÷ persediaan rata-rata sebagai proksi)
   - Kasus batas: `Σdemand = 0` → fill_rate & service_level = 1, stock_out_rate = 0; `rata-rata(supply) = 0` → turnover = 0. Nilai fraksi 0..1, dibulatkan 4 desimal.
3. **Dua scope per run** (user memilih "keduanya", supaya dashboard bisa membuktikan perbaikan kinerja thesis) — tabel `inventory_metrics` mendapat kolom tambahan **`scope`** (`baseline` / `forecastiq`), additive di luar skema §4 doc:
   - `scope='baseline'` (per **produk**): `demand=actual`, `supply=planning` dari `demand_history` — kinerja inventory kondisi EXISTING perusahaan.
   - `scope='forecastiq'` (per **produk**): `demand=actual`, `supply=forecast ForecastIQ` dari `forecast_results.forecast_data`, diselaraskan per periode (`date`). Hanya periode yang beririsan yang dihitung; bila horizon forecast run tidak beririsan dengan periode historis `demand_history`, baris `forecastiq` tidak dihasilkan (bukan error). Pada data simulasi thesis (forecast/planning/actual di periode yang sama) irisan tersedia → angka riil.
   - Fungsi metrik murni identik untuk kedua scope; hanya sumber `supply` yang berbeda. `scope` membuat penambahan sumber supply lain di masa depan cukup ubah orkestrasi, tanpa ubah engine.
4. **Endpoint `GET` (bukan `POST`)** sesuai kontrak §5 — metrik & cost-summary dihitung dari data run tersimpan tanpa input request-time (beda dari reorder yang butuh `current_stock`), jadi larangan #18 tidak berlaku; dihitung lazily saat `GET`, hasil `inventory_metrics` dipersist (replace-per-run) untuk dashboard.

---

## Fase Migrasi 8 — Planner Override untuk Entitas Baru (26 Juli 2026)

### Konteks
`overrides` + `override_service.py` (append-only, `reason` wajib, `OVERRIDE_REASON_REQUIRED`, `OVERRIDE_TARGET_NOT_FOUND`) **dipertahankan penuh** dari v2.0 — tidak ada perubahan skema/logic inti. Tambahan v3.0: `target_type` kini bisa merujuk **`material_requirement`** (selain `forecast_result`/`reorder_recommendation`), sesuai AGENTS.md §5 "setiap forecast_result, material_requirement, dan reorder_recommendation harus bisa di-override".

### Keputusan
1. **Tanpa tabel/kolom baru.** Mekanisme polimorfik yang sudah ada (dict `resolvers` target_type→fetcher + `SNAPSHOT_BUILDERS` target_type→snapshot) cukup diperluas satu entri, bukan ditulis ulang.
2. **Resolver** `material_requirement` → `SqlMaterialRequirementRepository.get_requirement` (sudah ada sejak Fase 5), didaftarkan di `deps.py` (TODO Fase 8 di komentar deps dihapus).
3. **Snapshot builder** `_snapshot_material_requirement` menyimpan `forecast_qty`, `standard_usage_qty`, `actual_usage_qty`, `buffer_stock_pct` sebagai `previous_value` (audit trail). Data asli `material_requirements` tidak diubah (append-only).
4. **Schema** `OverrideCreateRequest.target_type` (Literal) diperluas dengan `material_requirement` — nilai di luar tiga itu tetap otomatis 422.
5. `OVERRIDE_TARGET_NOT_FOUND` tervalidasi juga untuk `target_type` baru (test regresi + test baru). Tidak ada error code baru.

---

## Fase Migrasi 9 — Dashboard & Export (backend) (27 Juli 2026)

### Konteks
Fase 9 = dashboard diperluas + export diperluas + cutover final. Bagian **backend** (dashboard summary + export kolom) dikerjakan lebih dulu (TDD); frontend widget baru & cutover destruktif menyusul (butuh keputusan user).

### Keputusan
1. **Dashboard additive, bukan rewrite.** `DashboardService` mendapat 2 repo opsional (`warehouse_repo`, `inventory_metrics_repo`, default `None`) → widget `warehouse` & `inventory_metrics` bernilai `null` bila repo tak disuntik, sehingga test & pemakaian v2.0 (4 argumen posisional) tidak putus. Ditambah ke ringkasan run terakhir: `total_inventory_cost` (Σ TIC reorder recs), `avg_mape` (metrik v3.0 di samping `avg_mase` legacy). Metrik inventory dirata-rata per scope (`baseline`/`forecastiq`).
2. **Export backward-compatible.** Kolom EOQ/biaya (`buffer_stock`, `eoq_qty`, `ordering_cost`, `holding_cost`, `total_inventory_cost`) ditambah **setelah** kolom lama di reorder xlsx — `status` tetap kolom 5, jadi konsumen/tes lama tidak bergeser. Rec lama tanpa field baru → sel kosong (`getattr(..., None)`).
3. **Cutover butuh persetujuan user** (destruktif) — disetujui user 27 Juli 2026 ("sesuaikan dengan v3.0 saja dan tolong merge"), lihat sub-bagian di bawah.

### Cutover ke v3.0-only (27 Juli 2026)
1. **Drop kolom legacy** `forecast_results.data_profile` (kuadran ADI/CV² v2.0) dan `forecast_results.material_id` (+ index `ix_forecast_results_material_id`) via migration `b8c9d0e1f2a3`. Diverifikasi lebih dulu: kedua kolom **tidak ditulis** (`ForecastResult(...)` hanya mengisi `product_id`) dan **tidak dibaca/difilter** kode aktif; tak ada test yang mengisinya. Migration reversible (downgrade re-add kolom nullable + index). Model `forecast_result.py` disinkronkan (kolom dihapus).
2. **`consumption_history` TIDAK di-drop** (27 Juli 2026). Dinilai masih terjalin di jalur upload/ingestion raw-material v2.0 (`uploads.py`, `deps.py`, `cleanup_temp_uploads.py`, `reorder_service`, `preprocessing`) yang sengaja dipertahankan untuk forecasting raw material di luar scope thesis (§Keputusan Terbuka v3.0 poin 1/2). Meng-drop-nya dinilai = rewrite jalur itu, di luar maksud "sesuaikan v3.0 saja". → **Dibalik 4 Agustus 2026, lihat §Pensiun Jalur Raw-Material v2.0 di bawah.**
3. **Engine legacy** (`engines/legacy/`, `forecasting/legacy/`) tetap ada, tidak dihapus (AGENTS.md larangan #16).
4. **Merge** `migration/v3-thesis` → `main` (`--no-ff`, riwayat per-fase dipertahankan). Backend 332 test + frontend 53 test hijau sebelum merge.

---

## Pensiun Jalur Raw-Material v2.0 (4 Agustus 2026)

### Konteks & Trigger

Audit pasca-cutover mencari dead code dengan pola yang sama seperti yang menyingkap endpoint `material-requirements` hilang. Ditemukan `SqlConsumptionHistoryRepository.list_for_material` nol pemanggil. Penelusuran lanjutan menunjukkan asumsi di §Cutover poin 2 (**"masih terjalin di jalur upload/ingestion raw-material v2.0"**) **sudah tidak benar sejak Fase Migrasi 3**:

| Klaim 27 Juli | Kenyataan 4 Agustus |
|---|---|
| `uploads.py` menulis consumption | `UploadService` menulis `demand_history`; nama fungsi endpoint saja yang masih `upload_consumption_history` (kini di-rename) |
| ingestion menerima raw material | `REQUIRED_COLUMNS` = `{product_code, period, actual}` — upload `material_code` **ditolak**, tabel mustahil terisi |
| `reorder_service` membaca consumption | μ/σ diambil dari breakdown BOM atas forecast produk; `demand_stats` nol pemanggil |
| `cleanup_temp_uploads` memakainya | merakit `UploadService` dengan keyword usang → `TypeError`, job memang tidak pernah jalan (lihat bugfix terpisah) |

Jadi tabelnya bukan "jarang dipakai" melainkan **mati total**: tidak bisa diisi, tidak pernah dibaca.

### Keputusan

User memilih **drop & bersihkan** (4 Agustus 2026), sekaligus **melepas §Keputusan Terbuka v3.0 poin 1** (mempertahankan forecasting raw material langsung) dari scope v3.0.

1. **Migration `c9d0e1f2a3b4`** — drop tabel `consumption_history` + 3 indeksnya. Reversible: `downgrade()` membuat ulang struktur persis definisi `9a85016d7be7`. **Isi baris tidak kembali** — backup dulu bila instance produksi masih menyimpan histori v2.0 yang bernilai.
2. **Dihapus dari kode**: `models/consumption_history.py`, `SqlConsumptionHistoryRepository`, `reorder_service.demand_stats` (dead), import terkait di `deps.py` & `models_registry.py`, test `test_consumption_bulk_add`.
3. **Endpoint di-rename** `upload_consumption_history` → `upload_demand_history` (nama fungsi internal; path `POST /api/v1/uploads` tidak berubah, **bukan breaking change**).
4. **Engine legacy TETAP** di `engines/legacy/` & `forecasting/legacy/` — keputusan terpisah (§Keputusan Terbuka poin 2, AGENTS.md larangan #16) dan masih berlaku.
5. **Konsekuensi yang dicatat di PRD**: menghidupkan lagi jalur raw material bukan sekadar mengubah `FORECAST_ENGINES_ENABLED` — butuh tabel histori baru, mode ingestion `material_code`, dan jalur forecast/reorder level material.

Backend 339 test hijau (turun 1 karena test repo yang dihapus), coverage 92.42%.

---

## Redesign Frontend ke shadcn/ui (11 Agustus 2026)

### Konteks & Trigger

`components.json` sudah ada sejak awal tapi hanya satu komponen yang pernah digenerate
(`button.tsx`); sisanya `<table>`/`<input>` bergaya manual. Navigasi bernama `SidebarNav`
padahal merender bar horizontal di header. Redesign menyeluruh dikerjakan di branch
`feat/frontend-redesign` (backend tidak disentuh sama sekali).

### Keputusan

1. **Tetap Tailwind v3.4, tidak naik ke v4.** Diverifikasi langsung ke registry shadcn:
   `/r/styles/new-york/*.json` masih menyajikan `cssVars` format HSL + field
   `tailwind.config` untuk di-patch, jadi jalur v3 hidup penuh di CLI 4.16.2. Migrasi v4
   menuntut ganti plugin postcss, memindahkan konfigurasi ke `@theme` di CSS, dan menaikkan
   batas browser (Safari 16.4+) — pekerjaan yang layak diverifikasi sendiri, bukan
   ditumpangkan ke redesign.
2. **TanStack Table dipatok `8.21.3` (exact), bukan v9.** `npm install` memasang v9 sebagai
   mayor terbaru dengan API yang berbeda total (`useTable`, `createCoreRowModel`, sistem
   *feature*). Dokumentasi data table shadcn — rujukan yang akan dicari orang saat menyentuh
   tabel ini — seluruhnya v8, dan `data-table` **bukan** item registry (dicek: 404) sehingga
   tidak ada jalur CLI yang menambalnya otomatis. Pilihan versi dikurung di
   `components/common/DataTable.tsx`; pindah ke v9 = menyunting satu berkas.
3. **CLI shadcn tidak menambal semuanya — tiga celah ditutup manual.** `bg-popover`/
   `text-popover` dipakai `dialog`/`dropdown-menu`/`select`/`popover`/`command` tapi
   `--popover` tidak ikut ditulis ke `globals.css` maupun `tailwind.config.ts` (latar
   dropdown jadi transparan); `tailwindcss-animate` tidak ikut terpasang padahal 12 utility
   animasinya dipakai; keyframes accordion belum ada. Ketiganya bug diam — build tetap lolos.
4. **Token `--chart-1..5` dan `--success` dihitung, bukan dipilih dengan mata.** Palet chart
   divalidasi terhadap surface tiap mode (terang `#ffffff`, gelap `#020817`): lolos lightness
   band, chroma floor, CVD ΔE 9,1/8,4, normal-vision ΔE 19,6/19,3. Urutan slot adalah
   mekanisme keamanan buta warna — **jangan diacak dan jangan diputar untuk seri ke-6**.
   `--chart-3/4/5` di mode terang berada di bawah kontras 3:1, jadi chart terang yang memakai
   slot 3 ke atas wajib membawa label langsung atau tampilan tabel (chart yang ada sekarang
   hanya memakai slot 1–2, jadi belum terikat). `--success` diverifikasi 5,07:1 di terang dan
   11,45:1 di gelap.
5. **`src/lib/navigation.ts` jadi sumber tunggal struktur navigasi.** Sidebar dan breadcrumb
   membaca daftar yang sama supaya tidak bisa saling tidak sinkron.
6. **`src/lib/format.ts` memusatkan format angka.** Sebelumnya `MaterialRequirementsTable`
   dan `CostSummaryCard` punya helper identik masing-masing sementara `ReorderTable` mencetak
   Decimal mentah (`22400.0000`). Semua fungsi menerima `string | number | null | undefined`
   karena backend menyerialisasi Decimal sebagai string (AGENTS.md §4); nilai kosong → `—`,
   tapi **nol tetap `0`**.
7. **Radix Select tidak menerima `value=""`,** padahal `""` adalah kontrak "mode otomatis" di
   `MethodSelector` dan "semua produk" di filter BOM. Dipakai sentinel internal yang
   diterjemahkan di batas komponen; test memastikan yang keluar ke pemanggil tetap `""`.
8. **`vitest.setup.ts` men-stub `matchMedia`, `ResizeObserver`, dan pointer capture.** Bukan
   kosmetik: tanpanya komponen sidebar dan Radix Select melempar di jsdom.

### Dua perubahan perilaku menyusul (11 Agustus 2026)

Awalnya keduanya ditinggalkan karena mengubah perilaku, bukan tampilan; atas permintaan user
diselesaikan sekalian di branch yang sama.

9. **Konfirmasi hapus.** `components/common/ConfirmDialog.tsx` (di atas `AlertDialog`) dipasang
   di tabel produk, material, dan BOM. `description` wajib dan berisi konsekuensi konkret —
   pertanyaan "Hapus produk?" saja tidak memberi tahu bahwa baris BOM yang menunjuk produk itu
   ikut terdampak. Label pemicu dan label konfirmasi sengaja **dibedakan** ("Hapus" vs
   "Ya, hapus produk"): Radix tidak melepas pemicu dari DOM saat dialog terbuka, jadi label
   kembar menyulitkan pengguna screen reader.
10. **`AuditTrail` akhirnya dirender** — di dalam dialog override `MaterialRequirementsTable`,
    sepanel di bawah formnya. Alasannya bukan sekadar "harus dipakai": planner perlu melihat
    apakah baris itu sudah pernah di-override dan dengan alasan apa **sebelum** menimpanya.

### Hasil

Frontend 129 test hijau (dari 66), typecheck & eslint bersih, build sukses. Komponen `ui/`
1 → 29. Halaman ber-`DataTable` naik ~50–65 kB First Load JS — kalau nanti terasa berat,
sasaran pertama adalah memuat `DataTable` secara dinamis.

## Migrasi Object Storage: Cloudflare R2 → IDCloudHost (20 Agustus 2026)

**Pemicu.** Rencana deployment bergeser dari Railway/Vercel ke VPS. Karena infrastruktur lain
pindah ke penyedia Indonesia, object storage ikut dipindah ke **IDCloudHost Object Storage**
supaya berada di region yang sama dengan aplikasi (latensi upload/export) dan satu tagihan.

**Kenapa perpindahannya murah.** `storage_service.py` sejak Fase 3 hanya memakai tiga operasi
S3 standar — `put_object`, `copy_object`, `delete_object` — tanpa presigned URL dan tanpa API
khas Cloudflare, dengan client boto3 di-inject lewat konstruktor. Jadi seluruh body service
**nol perubahan**; yang diganti hanya fungsi builder client-nya.

**Yang berubah:**

1. `build_r2_client()` → **`build_s3_client()`**. Endpoint tidak lagi diturunkan dari account ID
   (`https://{account}.r2.cloudflarestorage.com`) melainkan dibaca utuh dari `S3_ENDPOINT_URL`.
   Ini alasan utama env-nya di-*rename* dan bukan sekadar diisi nilai baru: bentuk URL R2
   men-encode asumsi vendor ke dalam kode.
2. Env `CLOUDFLARE_R2_ACCOUNT_ID/ACCESS_KEY/SECRET_KEY/BUCKET_NAME` →
   `S3_ENDPOINT_URL`, `S3_ACCESS_KEY`, `S3_SECRET_KEY`, `S3_BUCKET_NAME`, plus dua env baru:
   - **`S3_REGION`** (default `SouthJkt-a`). R2 memakai `region_name="auto"`, yang **hanya**
     valid di R2 — signature v4 ikut menandatangani region, jadi nilai `auto` ditolak provider lain.
   - **`S3_ADDRESSING_STYLE`** (default `auto`). Virtual-host style (`{bucket}.{endpoint}`)
     butuh wildcard DNS di sisi provider; kalau ternyata tidak tersedia, set `path` **lewat env
     di server, tanpa deploy ulang kode**. Signature dipatok `s3v4`.
3. Komentar/docstring yang menyebut "R2" sebagai penyedia aktual diganti "object storage".
   Yang menyebut R2 sebagai *contoh* provider dipertahankan.

**Yang TIDAK berubah:** layout key (`temp/uploads/…`, `permanent/datasets/…`,
`permanent/exports/…`) identik, jadi tidak ada migrasi skema. Kalau nanti sudah ada data
produksi di R2, pindahnya cukup `rclone sync`. Per tanggal ini belum pernah deploy, jadi
tidak ada data yang perlu dipindah.

**Belum diverifikasi terhadap server sungguhan.** Test memakai client boto3 yang di-mock
(`370 passed, 1 skipped`). Yang masih perlu dicek saat kredensial IDCloudHost sudah ada:
apakah `copy_object` didukung penuh (dipakai `move_to_permanent`), dan apakah addressing style
`auto` bekerja atau harus dipaksa `path`.

## Deployment: Railway/Vercel → VPS Self-Hosted (20 Agustus 2026)

**Pemicu.** Audit kesiapan deploy: kode sudah hijau (backend 370 test, frontend 129 test,
`next build` sukses), tapi **tidak ada satu pun artefak deployment yang layak production**.
`docker-compose.yml` yang ada adalah compose *dev* — bind-mount source, `uvicorn --reload`,
frontend dijalankan dengan `npm run dev`. Menjalankan itu di VPS berarti menjalankan dev
server sebagai production.

**Temuan paling serius: tidak ada `.dockerignore` di mana pun.** `backend/Dockerfile` memakai
`COPY . .`, jadi `backend/.env` (kredensial) dan `backend/.venv` (553 MB, interpreter 3.14 yang
tidak kompatibel dengan image 3.11) ikut masuk image. File `.env` di dalam image bukan sekadar
boros: `docker history` menyimpan layer selamanya, jadi kredensial tetap terbaca meski file
dihapus di layer berikutnya. Ini ditambal duluan sebelum image pertama pernah di-build.

**Keputusan & alasannya:**

1. **Compose production terpisah, bukan menambal compose dev.** Perbedaannya terlalu
   fundamental (bind-mount vs image, reload vs tidak, port publish vs tidak) — satu file
   dengan override akan menyembunyikan perbedaan yang justru harus terlihat.
2. **Caddy, bukan Nginx.** TLS Let's Encrypt otomatis termasuk perpanjangan; Nginx butuh
   certbot + cron sendiri. Untuk deployment satu domain, konfigurasi Caddy ±30 baris.
3. **Satu domain untuk frontend & backend** (`/api/*` + `/health` → backend, sisanya →
   frontend). Konsekuensinya request API jadi same-origin, jadi seluruh kelas bug CORS di
   production hilang, bukan sekadar dikonfigurasi dengan benar.
4. **Migrasi di entrypoint container, bukan langkah deploy manual.** `set -e` membuat
   container gagal start kalau `alembic upgrade head` gagal — disengaja: aplikasi hidup di
   atas skema yang salah lebih berbahaya daripada aplikasi yang tidak hidup. Bisa dimatikan
   lewat `RUN_MIGRATIONS=false` untuk kasus rollback manual.
5. **Port aplikasi tidak di-publish ke host.** Backend/frontend/Postgres hanya ada di jaringan
   internal compose; satu-satunya pintu masuk adalah Caddy di 80/443. Compose dev sebelumnya
   mem-publish Postgres ke `0.0.0.0:5432` dengan password `forecastiq/forecastiq` — aman di
   laptop, fatal di VPS.
6. **Non-root user di kedua image** + healthcheck yang dipakai compose (`depends_on:
   condition: service_healthy` pada Postgres, supaya migrasi tidak jalan sebelum DB siap).
7. **`output: "standalone"` di `next.config.mjs`** — image runner cuma butuh `server.js` +
   node_modules minimal (66 MB) alih-alih seluruh `node_modules` (±500 MB).
8. **`FORECAST_ENGINES_ENABLED` di `.env.prod.example` sengaja tanpa `lstm`.** TensorFlow masih
   di-comment di `requirements.txt`, jadi `lstm` akan di-exclude otomatis oleh engine. Lebih
   baik ketiadaannya eksplisit di konfigurasi daripada tampak aktif tapi diam-diam dilewati.

**Jebakan yang didokumentasikan, bukan dihilangkan:** `NEXT_PUBLIC_*` di-inline ke bundel saat
`next build`, jadi mengubahnya di `.env.prod` tanpa `--build` tidak berpengaruh. Ini sifat
Next.js, bukan bug — dicatat di Dockerfile, compose, `.env.prod.example`, dan §10.

**Belum terverifikasi:** Docker daemon di mesin dev sedang mati saat pekerjaan ini dilakukan,
jadi `docker compose ... config` sudah divalidasi (exit 0) dan `next build --standalone` sudah
terbukti menghasilkan `server.js`, tapi **kedua image belum pernah benar-benar di-build**.
Ini juga yang membuat item "verifikasi image Docker backend" di `TASK_BREAKDOWN.md` §10 tetap
terbuka.

---
*Dokumen ini adalah working note, bukan bagian dari deliverable utama — tapi disimpan agar keputusan tidak hilang/terulang tanya lagi di masa depan.*