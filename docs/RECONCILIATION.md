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
*Dokumen ini adalah working note, bukan bagian dari deliverable utama — tapi disimpan agar keputusan tidak hilang/terulang tanya lagi di masa depan.*