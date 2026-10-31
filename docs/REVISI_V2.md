# Change Request v3.2 — Sinkronisasi ForecastIQ dengan Konteks Thesis Terbaru

| | |
|---|---|
| **Tanggal** | 26 Oktober 2026 |
| **Sumber baru** | `Simulasi Thesis 2.xlsx` (vs `Simulasi Thesis.xlsx`), `Rumus thesis untuk program.docx` |
| **Baseline sistem** | Repo `budipriyoutomo/forecasting-thesis` @ `7c2806d` ("update master data") — termasuk keputusan 24 Agustus & 2 Oktober 2026 di `docs/RECONCILIATION.md` |
| **Peran penilai** | PPIC / Product Owner / Software Architect |
| **Status** | Keputusan §6 dijawab lengkap · Fase 11.0–11.8 ✅ diimplementasi 30 Okt 2026 (termasuk export proyeksi & metrik) |

---

## 1. Ringkasan Eksekutif

Konteks baru **mengubah alur sistem**, bukan sekadar menambah rumus. Thesis sekarang mendefinisikan pipeline 4 tahap yang eksplisit (sheet *Diagra Alur Sistem* + *Flow Chart Program*):

```
[1] Forecast produk jadi (FG)
        │  hasil ramalan terbaik (MAD/MFE/MAPE)
        ▼
[2] MRP = Forecast × BOM → Safety stock, Buffer stock, EOQ
        │  qty pemesanan material
        ▼
[3] Capacity constraint gudang (level MATERIAL, pallet → CTN → pcs)
        │  stock awal + kedatangan − pemakaian = stock akhir → utilisasi %
        ▼
[4] Evaluasi usulan inventory (MATERIAL)
        service level, stockout rate, inventory turnover (hari),
        ordering / holding / shortage cost
```

**5 temuan paling penting:**

1. 🔴 **Kapasitas gudang pindah ke level material** — bertentangan langsung dengan keputusan 24 Agustus 2026 (kapasitas per *produk*). Ini keputusan terbesar.
2. 🔴 **EOQ berubah ke rumus klasik** `EOQ = √(2AS / iC)` — sistem sekarang pakai EOQ dinamis `TC = nS + Σ(Iₜ·H)`.
3. 🔴 **Bug satuan di safety stock & ROP** — σ dan μ diambil dari deret forecast per *periode* (bulanan) lalu dikali `lead_time_days`. Untuk data bulanan, ROP membengkak ~30×. Harus diperbaiki terlepas dari thesis.
4. 🔴 **Buffer stock tidak pernah terisi & rumusnya terbalik** — `max(0, standar − aktual)` selalu 0 saat ada waste (aktual > standar). Thesis kini pakai rasio `aktual : standar`.
5. 🟡 **Konsep stok baru** — stock awal (upload dari ERP), estimasi kedatangan material, stock akhir, dan utilisasi gudang. Sistem saat ini tidak punya entitas stok sama sekali (`current_stock` hanya parameter request).

---

## 2. Apa yang Berubah di Sumber

### 2.1 `Simulasi Thesis.xlsx` → `Simulasi Thesis 2.xlsx`

| Sheet | Status | Isi perubahan | Dampak ke sistem |
|---|---|---|---|
| Bab I Plan vs Forecast | Tidak berubah (nilai identik) | — | Tidak ada. Catatan: baris 2025 di tabel gap (C5:N5) masih `#REF!` |
| Bab II Kerangka Pemikiran | Diubah | Tambah kotak **Feature Selection — Embedded RF/XGBoost feature importance** | Forecasting engine (§3.6) |
| Tahapan Penelitian | Tidak berubah | — | — |
| Bab II Posisi Penelitian | Tidak berubah | — | — |
| Bab II Penelitian Terdahulu | Diubah | Tambah kolom `No` (penomoran B5–B7 masih hardcode, B7 duplikat "4") | Tidak ada (dokumen akademik) |
| **Pengumpulan Data** | **Baru** | BOM 6 produk (level 0–2) + header "Kapasitas Gudang" (belum ada data) | Master BOM, kapasitas material (§3.2, §3.3) |
| **Flow Chart Program** | **Baru** | Diagram alur program end-to-end | Seluruh pipeline (§1) |
| **Diagra Alur Sistem** | **Baru** | White-box 4 tahap: Input → Proses → Output | Seluruh pipeline (§1) |

### 2.2 `Rumus thesis untuk program.docx` (baru) — rumus kunci

| Rumus | Definisi di dokumen |
|---|---|
| Exponential Smoothing α | Data bergejolak: 0,8 / 0,95 / 0,99 · Data stabil: 0,2 / 0,15 / 0,05 / 0,01 · Coba satu per satu, pilih **MAD** terbaik |
| MAD / MFE / MAPE | Standar; MFE positif = *under-estimate*, negatif = *over-estimate*; MAPE disertai tabel interpretasi |
| MRP | Forecast × qty BOM |
| Safety stock | `SS = Z × STD × √L` — **STD harian**, **L dalam hari**, Z dari tabel service level (95% / 99%) |
| Buffer stock | `Aktual pemakaian : Standar pemakaian`; Standar = output produksi × BOM |
| EOQ | `EOQ = √(2AS / iC)` — A = demand **tahunan**, S = biaya pesan, i = % biaya simpan **tahunan**, C = harga material/unit |
| Total cost | `TC = (A/Q)·S + (Q/2)·i·C` |
| Biaya pembelian | qty beli × harga material |
| Biaya simpan | Fasilitas = 0 (in-plant) · TK langsung Rp 3.972.202 × 12 × 2 orang = **Rp 95.332.848/tahun** · Utility (listrik, depresiasi lampu) · Depresiasi rak, pallet, handpallet + depresiasi & perawatan forklift |
| Inventory turnover | **(hari)** = rata-rata persediaan per bulan ÷ rata-rata pemakaian per hari |
| Shortage cost | Qty forecast tidak terpenuhi × harga produk (minuman) |
| Service level, stockout rate | Disebut, rumus belum ditulis di dokumen |

---

## 3. Gap Analysis: Thesis Baru vs Sistem Saat Ini

Legenda prioritas: **P0** = salah secara matematis / blokir klaim thesis · **P1** = wajib untuk thesis · **P2** = peningkatan.

### 3.1 Pipeline & Orkestrasi

| | |
|---|---|
| **Thesis** | Satu alur berantai: forecast → MRP → qty pesan → validasi kapasitas → evaluasi. Output tiap tahap jadi input tahap berikutnya. |
| **Sistem** | Endpoint terpisah dan independen: `reorder`, `warehouse-validation`, `cost-summary`, `inventory-metrics`. Validasi gudang membaca **forecast produk**, tidak membaca hasil reorder. |
| **Perubahan** | Tambah orkestrator `planning_pipeline_service.py` (atau perluas `forecast_run_service`) yang menjalankan tahap 2→4 berurutan untuk satu `run_id`, dengan tiap tahap tetap fungsi murni yang bisa dites terpisah. Endpoint lama tetap ada. |
| **Prioritas** | P1 |

### 3.2 Kapasitas Gudang — pindah ke level material ⚠️ konflik keputusan

| | |
|---|---|
| **Thesis** | Input tahap 3 = **qty pemesanan material**. Kapasitas "by pallet → konversi CTN dan pcs". Rumus: `Stock akhir = (Stock awal + Estimasi kedatangan) − Estimasi pemakaian`; `Utilisasi = Stock / Kapasitas × 100%` (untuk stock awal & stock akhir). |
| **Sistem** | `warehouse_config` 1 baris per **produk** (unique `product_id`), validasi = Σ forecast produk ≤ `capacity_qty`. Keputusan user 24 Agustus & 2 Oktober 2026. |
| **Rekomendasi** | Generalisasi, bukan rewrite: ganti `product_id` jadi target polimorfik `item_type` (`product`/`material`) + `item_id`. Logika `compute_effective_capacity` (pallet/dus/pcs) **dipakai ulang apa adanya** — untuk material, "dus" = CTN. Default thesis = `material`. |
| **Alasan tidak hapus level produk** | Gudang FG dan gudang packaging adalah dua gudang berbeda di dunia nyata; level produk tetap bernilai sebagai fitur produk (bukan klaim thesis). Tapi kalau Anda ingin satu model saja, hapus level produk — lebih sederhana. → **Keputusan #1** |
| **Prioritas** | P0 untuk thesis |

### 3.3 Stok, Kedatangan Material, Stock Akhir & Utilisasi — entitas baru

| | |
|---|---|
| **Thesis** | Stock awal = real-time stock **upload dari ERP**; estimasi kedatangan = **input manual / upload Excel**; estimasi pemakaian = **rencana produksi × BOM**. |
| **Sistem** | Tidak ada. `current_stock` hanya parameter body `POST /reorder/recommendations` (keputusan #16 git). |
| **Perubahan** | Tabel baru `stock_snapshots` (per material per tanggal, sumber upload) dan `material_receipts` (rencana kedatangan per material per periode). Proyeksi stok per periode horizon: `ending[t] = opening[t] + receipts[t] − usage[t]`, `opening[t+1] = ending[t]`. Keputusan #16 direvisi: `current_stock` di request jadi **fallback** bila belum ada snapshot. |
| **Pertanyaan** | "Rencana produksi" = forecast ForecastIQ, atau planning perusahaan? → **Keputusan #3** |
| **Prioritas** | P0 untuk thesis |

### 3.4 BOM Multi-Level

| | |
|---|---|
| **Thesis** | Level 0 FG → Level 1 Cap + Bottle White → **Level 2 Preform White** (komponen Bottle). Bottle & Preform dipakai bersama oleh semua produk. |
| **Sistem** | `boms` single-level (`product_id` → `material_id`). Preform tidak bisa direpresentasikan sebagai turunan Bottle. |
| **Perubahan** | Tambah `parent_material_id` (nullable) di `boms` **atau** tabel `material_boms` (material → material). Explosion rekursif di `bom_service.breakdown_requirements_series` (agregasi lintas produk sudah benar). Guard siklus (A→B→A) → error baru `BOM_CYCLE_DETECTED`. |
| **Pertanyaan** | Apakah Bottle dibuat in-house dari Preform (blow molding)? Jika ya, yang dipesan ke supplier hanya **Preform + Cap**, dan Bottle hanya WIP → EOQ & kapasitas dihitung untuk Preform, bukan Bottle. → **Keputusan #4** |
| **Prioritas** | P1 |

**Masalah data BOM yang perlu dibereskan dulu:**

| Kode BOM | Produk di Bab I | Status |
|---|---|---|
| Yoghurt PL | KBYPL 200 — Original | ✅ cocok |
| Yoghurt BB | KBYBB 200 — Blueberry | ✅ cocok |
| Yoghurt LY | KBYLY 200 — Lychee | ✅ cocok |
| Yoghurt BF | KBYBF 200 — Black Fruit | ✅ cocok |
| Yoghurt MG | KBYMG 200 — Mangga | ✅ cocok |
| Yoghurt **SB** | KBY**ST** (Strawberry) atau KBY**SR** (Slimberries)? | ❌ ambigu |
| — | Satu dari ST/SR | ❌ tidak punya BOM |

Semua `Qty = 1` dan semua UOM `PCS` → aman untuk thesis, tapi pastikan template import BOM mewajibkan kode yang sama persis dengan `products.code` (`KBYxx 200`, bukan "Yoghurt xx").

### 3.5 EOQ — klasik vs dinamis

| | |
|---|---|
| **Thesis** | `EOQ = √(2AS / iC)`, `TC = (A/Q)S + (Q/2)iC`. Butuh **A tahunan**, **i (%)**, **C = harga material**. |
| **Sistem** | `compute_eoq` = EOQ dinamis (simulasi n = 1..T, pilih TC minimum). Holding cost **H flat per unit per periode** dari template biaya. |
| **Perubahan** | Tambah `compute_eoq_classic(annual_demand, ordering_cost, holding_rate, unit_price)` sebagai fungsi murni baru. Pilih via env `EOQ_METHOD=classic|dynamic` (default `classic` = thesis). `compute_eoq` dinamis **tidak dihapus** (pola sama seperti engine legacy). A = forecast horizon di-annualisasi (`Σ forecast ÷ n_bulan × 12`). |
| **Konsekuensi** | `materials.unit_price` (saat ini nullable, informasi saja) **menjadi wajib** untuk EOQ klasik. Material tanpa harga → status per-item `MISSING_UNIT_PRICE`, bukan menggagalkan run. Template biaya perlu field `holding_cost_rate_pct` (i). |
| **Pertanyaan** | Bagaimana i (%) diturunkan dari biaya absolut (TK Rp 95,3 jt/thn + utility + depresiasi)? Usulan: `i = Σ holding cost tahunan ÷ rata-rata nilai persediaan (Rp)`. → **Keputusan #5** |
| **Prioritas** | P0 untuk thesis |

### 3.6 Forecasting Engine

| # | Thesis | Sistem | Perubahan | Prio |
|---|---|---|---|---|
| a | α ES: {0,01; 0,05; 0,15; 0,2} stabil, {0,8; 0,95; 0,99} bergejolak; pilih by **MAD** | `_ALPHA_GRID` 0,1–0,9, pilih by **MAPE** | Ganti grid ke union 7 nilai thesis (env `ES_ALPHA_GRID`), metrik pemilihan α ke `MAD` (env `ES_ALPHA_METRIC`) | P1 |
| b | Metrik uji: **MAD, MFE, MAPE** | MAD, MFE, MSE, MAPE (+ MASE), ranking default `mape` | MSE tetap disimpan tapi disembunyikan dari laporan thesis. Konfirmasi metrik ranking antar-metode → **Keputusan #6** | P1 |
| c | Tabel interpretasi MAPE | Tidak ada | Tambah label di `explanation`: <10% sangat baik, 10–20% baik, 20–50% cukup, >50% buruk (sesuaikan dengan tabel di docx) | P2 |
| d | **Feature Selection** — embedded RF/XGB feature importance (step baru di Kerangka) | Tidak disimpan | Simpan `feature_importances_` ke `forecast_results.feature_importance` (JSONB), tampilkan di halaman hasil | P1 |
| e | **Hyperparameter tuning — Grid Search** | XGB pakai parameter tetap (docstring menyebut grid search rapuh untuk data pendek); RF juga tetap | Implementasikan `GridSearchCV` dengan `TimeSeriesSplit`, aktif via env `ML_GRID_SEARCH=true`. Tetap catat limitasi data pendek di thesis | P1 |
| f | Pre-processing: cleaning, transformasi, feature engineering, scaling, **handling outliers**, structuring, splitting | Outlier handling hanya ada di `legacy/classification.py` | Pindahkan deteksi IQR ke `preprocessing.py`, opsional winsorize sebelum training ML | P2 |
| g | Variabel: musim, cuaca & temperatur, harga, promosi & event | Hanya lag + kalender | Kolom opsional di upload (`price`, `promo_flag`, `event_flag`, `temperature`) — dipakai bila ada. Jika data tidak tersedia, thesis harus menyatakannya sebagai batasan → **Keputusan #7** | P2 |
| h | Input: "data historis **aktual planning** 2024–2025" | Target training = kolom `actual` | Konfirmasi target → **Keputusan #2** | P0 |

### 3.7 Safety Stock & Reorder Point — bug satuan

```python
# reorder_service.generate_for_run (sekarang)
mu    = mean(material_series)          # per PERIODE forecast (bulanan di data thesis)
sigma = std(material_series)           # per PERIODE
ss    = z * sigma * sqrt(lead_time_days)   # ❌ σ bulanan × √hari
rop   = mu * lead_time_days + ss           # ❌ μ bulanan × hari → ~30× terlalu besar
```

| | |
|---|---|
| **Thesis** | STD = standar deviasi demand **harian**, L dalam **hari**. |
| **Perubahan** | Konversi eksplisit dari periode ke harian: `μ_d = μ_p / days_in_period`, `σ_d = σ_p / √days_in_period` (asumsi independensi harian, dicatat sebagai asumsi di thesis). `days_in_period` dari `infer_period_delta` yang sudah ada. |
| **Tambahan** | `SERVICE_LEVEL_Z = 1.65` hardcode → ganti input `SERVICE_LEVEL_PCT` (95 / 99), Z dihitung `scipy.stats.norm.ppf`. |
| **Test wajib** | Kasus data bulanan, lead time 7 hari: ROP harus ≈ μ_bulanan × 7/30 + SS, bukan μ_bulanan × 7. |
| **Prioritas** | **P0 — bug, perbaiki terlepas dari thesis** |

### 3.8 Buffer Stock — rumus & wiring

| | |
|---|---|
| **Thesis** | `Buffer = Aktual pemakaian : Standar pemakaian`, Standar = output produksi × BOM. Tujuan: antisipasi waste. |
| **Sistem** | `compute_buffer_stock` = `max(0, standar − aktual)`. Saat ada waste (aktual > standar) hasilnya **selalu 0**. Selain itu `generate_for_run` **tidak pernah mengisi** `buffer_stock` (kolom ada, tidak dihitung). |
| **Perubahan** | (1) Fungsi murni baru `compute_waste_factor(actual, standard) = actual / standard`; buffer qty = `(factor − 1) × kebutuhan material periode`. (2) Data input baru: pemakaian aktual material + output produksi aktual per periode (upload). (3) Wiring ke `generate_for_run` dan ke validasi kapasitas (buffer ikut menempati gudang). |
| **Pertanyaan** | Bagaimana rasio diterjemahkan jadi qty buffer? Usulan di atas `(factor − 1) × kebutuhan` → **Keputusan #8** |
| **Prioritas** | P0 |

### 3.9 Evaluasi Kinerja Inventory — pindah ke material + metrik baru

| Metrik | Thesis | Sistem | Perubahan |
|---|---|---|---|
| Scope | **Material** ("Evaluasi usulan inventory (material)") | Produk (actual vs planning / forecast) | Tambah scope `material` di `inventory_metrics.target_type` (kolom sudah polimorfik); data dari proyeksi stok §3.3 |
| Service level / fulfillment rate | Ya | `fill_rate` & `service_level` (siklus) | Pertahankan, beri label "fulfillment rate" sesuai thesis |
| Stockout rate | Ya | Ada | Pertahankan |
| Inventory turnover | **Hari** = avg persediaan/bulan ÷ avg pemakaian/hari | Rasio Σ demand ÷ avg supply | Tambah `inventory_days`; rasio lama tetap |
| Ordering cost | Ya | Ada (dari EOQ) | Ikut rumus klasik §3.5 |
| Holding cost | Komponen rinci (TK, utility, depresiasi, perawatan forklift) | Template biaya: OVERHEAD + STORAGE_ASSET, saran H per dus/bulan | Tambah tipe item `MAINTENANCE`; basis tahunan; turunkan i (%) |
| **Shortage cost** | Qty tak terpenuhi × **harga jual produk** | Tidak ada | Fungsi baru, pakai `products.selling_price` (sudah ada sejak Fase 10) |
| Biaya pembelian | qty × harga | Ada (informasi, tidak masuk TIC) | Pertahankan |

Prioritas: P1.

---

## 4. Perubahan Data Model

Semua migration **additive** kecuali yang ditandai. Ikuti pola git: backup sebelum `alembic upgrade head`.

```text
warehouse_config
  + item_type      VARCHAR(10) NOT NULL DEFAULT 'product'   -- product | material
  + material_id    UUID NULL FK materials                  -- product_id jadi NULLABLE
  ~ unique         (item_type, product_id) / (item_type, material_id)
  CHECK            tepat satu dari product_id/material_id terisi sesuai item_type

boms
  + parent_material_id UUID NULL FK materials   -- BOM level-2 (material → material)
  (alternatif: tabel material_boms terpisah — lihat Keputusan #4)

stock_snapshots            -- 🆕 stock awal dari ERP
  id, material_id FK, snapshot_date DATE, qty NUMERIC, uom,
  upload_session_id FK NULL, created_at

material_receipts          -- 🆕 estimasi kedatangan
  id, material_id FK, expected_date DATE, qty NUMERIC,
  source VARCHAR(10) ('manual'|'upload'), note, created_by FK users, created_at

material_usage_history     -- 🆕 untuk buffer stock
  id, material_id FK, product_id FK NULL, period DATE,
  production_output NUMERIC, actual_usage NUMERIC, upload_session_id FK

stock_projections          -- 🆕 hasil tahap 3 per run
  id, run_id FK, material_id FK, period DATE,
  opening_qty, receipt_qty, usage_qty, order_qty, ending_qty,
  capacity_qty, utilization_opening_pct, utilization_ending_pct, is_within_capacity

reorder_recommendations
  + eoq_method      VARCHAR(10)   -- classic | dynamic
  + annual_demand   NUMERIC
  + unit_price_used NUMERIC NULL
  + holding_rate_used NUMERIC NULL
  + item_status     VARCHAR(30)   -- COMPLETED | MISSING_UNIT_PRICE
  ~ buffer_stock    -- sekarang benar-benar diisi

cost_templates
  + holding_cost_rate_pct NUMERIC NULL      -- i (%) tahunan
cost_template_items
  ~ item_type += 'MAINTENANCE'
  + period_basis VARCHAR(10) DEFAULT 'monthly'   -- monthly | annual

forecast_results
  + feature_importance JSONB NULL           -- RF/XGB
  + hyperparameters    JSONB NULL           -- hasil grid search

inventory_metrics
  + inventory_days NUMERIC NULL
  + shortage_cost  NUMERIC NULL
  ~ target_type    gunakan 'material' (kolom sudah polimorfik)
```

---

## 5. Perubahan API & Frontend

### 5.1 API (`/api/v1`)

```text
# Stok & kedatangan (🆕)
POST   /stock-snapshots/import            # upload stock ERP (Excel/CSV)
GET    /stock-snapshots?material_id=&date=
GET    /material-receipts
POST   /material-receipts                 # input manual
POST   /material-receipts/import          # upload Excel
PUT    /material-receipts/{id}
DELETE /material-receipts/{id}

# Pemakaian aktual (🆕, untuk buffer stock)
POST   /material-usage/import

# Pipeline (🆕) — POST generate, GET baca (pola keputusan #16)
POST   /forecast/runs/{run_id}/plan       # jalankan tahap 2→4 berurutan
GET    /forecast/runs/{run_id}/stock-projection

# Diubah
POST/PUT /warehouse/config                # + item_type, material_id
GET    /forecast/runs/{run_id}/warehouse-validation   # details bisa per material
GET    /forecast/runs/{run_id}/inventory-metrics?target_type=material
GET    /forecast/runs/{run_id}/cost-summary           # + shortage_cost, eoq_method
```

**Error code baru** (daftarkan di `AGENTS.md` §4 sebelum dipakai, larangan #13):
`BOM_CYCLE_DETECTED` (422), `STOCK_SNAPSHOT_NOT_FOUND` (404), `MATERIAL_RECEIPT_NOT_FOUND` (404), `MISSING_UNIT_PRICE` (status per-item, bukan HTTP error).

### 5.2 Frontend

| Halaman | Perubahan |
|---|---|
| Master Data → Kapasitas Gudang | Toggle target Produk / Material; label "Dus" → "CTN" untuk material |
| Master Data → BOM | Tampilan tree 3 level (FG → Cap/Bottle → Preform) |
| 🆕 Stok & Kedatangan | Upload stock ERP, tabel kedatangan (manual + import) |
| Hasil Forecast | Panel feature importance; label interpretasi MAPE; α terpilih untuk ES |
| 🆕 Proyeksi Stok per Material | Tabel per periode: opening / receipt / usage / order / ending + bar utilisasi % |
| Dashboard | Widget utilisasi gudang material, shortage cost, inventory days |

---

## 6. Keputusan yang Harus Dikonfirmasi (blocking)

| # | Pertanyaan | Rekomendasi saya | Kenapa penting |
|---|---|---|---|
| 1 | Kapasitas gudang: material saja, atau produk + material? | **Produk + material** (generalisasi polimorfik), thesis pakai material | Membalik sebagian keputusan 24 Agustus; menentukan migration |
| 2 | Target training model: `actual` atau `planning`? ("data historis aktual planning") | Ikuti definisi Bab III; jika "aktual planning" = rencana produksi final, target = `planning` | Menentukan seluruh angka akurasi thesis |
| 3 | "Rencana produksi" untuk estimasi pemakaian material = forecast ForecastIQ atau planning perusahaan? | Forecast ForecastIQ (skenario usulan) **dan** planning (skenario baseline) — keduanya dihitung untuk pembandingan | Menentukan input tahap 3 |
| 4 | Bottle dibuat in-house dari Preform? Material apa yang dipesan ke supplier? | Bila in-house: EOQ & kapasitas untuk **Preform + Cap**; Bottle = WIP | Menentukan item yang masuk EOQ |
| 5 | Cara menurunkan i (%) dari biaya simpan absolut? | `i = Σ holding cost tahunan ÷ rata-rata nilai persediaan (Rp)` | EOQ klasik tidak bisa jalan tanpa i |
| 6 | Metrik ranking antar-metode: MAD atau MAPE? | **MAD** — konsisten dengan pemilihan α di docx; MAPE untuk interpretasi | Menentukan metode pemenang per SKU |
| 7 | Variabel eksternal (cuaca, harga, promo, event) — ada datanya? | Bila tidak ada: nyatakan sebagai batasan thesis, sistem cukup siapkan kolom opsional | Kerangka Pemikiran menyebut variabel ini secara eksplisit |
| 8 | Rasio buffer stock (aktual : standar) diterjemahkan ke qty bagaimana? | `buffer_qty = (aktual/standar − 1) × kebutuhan material periode`, minimum 0 | Rumus docx hanya memberi rasio |

---

### 6.1 Jawaban (29 Oktober 2026)

| # | Jawaban | Konsekuensi |
|---|---|---|
| 1 | **Produk + material** | `warehouse_config` polimorfik (`item_type`), migration additive; thesis pakai `material` |
| 2 | **`actual`** | Target training tetap kolom `actual`; planning = baseline pembanding |
| 3 | **Keduanya** | Proyeksi stok dihitung 2 skenario: usulan (forecast) & baseline (planning) |
| 4 | **Bottle beli jadi** | EOQ & kapasitas untuk Cap + Bottle; Preform hanya informasi BOM level 2 (tidak masuk EOQ) → explosion rekursif 11.3 bisa disederhanakan |
| 5 | **Turunkan otomatis** | `i = Σ holding cost tahunan ÷ rata-rata nilai persediaan`, tampil sebagai saran, bisa di-override |
| 6 | **3 kolom ranking** | Hasil forecast menampilkan rank MAD, rank MFE (by \|MFE\|), rank MAPE di 3 kolom berdampingan sebagai bahan acuan planner. Pemenang otomatis ditentukan **master data Pengaturan Forecast** (default `mad`, bukan env — permintaan user 29 Okt). ✅ Selesai Fase 11.2a |
| 7 | **Semua tersedia** (musim, cuaca & temperatur, harga, promosi & event) | 🆕 **Master data variabel eksternal** dinamis: planner definisikan variabel (kode, nama, tipe numerik/flag, level global/per-SKU), toggle **aktif/nonaktif**; nilai per periode di-upload. Engine ML hanya memakai variabel aktif yang datanya lengkap untuk horizon. Masuk Fase 11.2 (sub-fase 11.2b) |
| 8 | **`max(0, aktual/standar − 1) × kebutuhan`** | Buffer = tambahan di atas kebutuhan material periode |

## 7. Urutan Implementasi (TDD, sesuai `AGENTS.md` §3)

| Fase | Isi | Bergantung pada | Estimasi |
|---|---|---|---|
| **11.0** ✅ | **Fix bug satuan SS/ROP** (§3.7) + `SERVICE_LEVEL_PCT` — selesai 29 Okt 2026 | — | 0,5 hari |
| 11.1 | Fix buffer stock: rumus rasio + wiring + upload `material_usage_history` | Keputusan #8 | 1–1,5 hari |
| 11.2 | Forecasting: α grid thesis, metrik α = MAD, ranking, label MAPE, feature importance, grid search | Keputusan #2, #6 | 2 hari |
| 11.3 | BOM multi-level + explosion rekursif + guard siklus; perbaiki data SB/ST/SR | Keputusan #4 | 1,5 hari |
| 11.4 | EOQ klasik + `holding_cost_rate_pct` + `MISSING_UNIT_PRICE` | Keputusan #5 | 1,5 hari |
| 11.5 | Stok & kedatangan: `stock_snapshots`, `material_receipts`, import | — | 2 hari |
| 11.6 | Kapasitas material + `stock_projections` + utilisasi | 11.3, 11.5, Keputusan #1, #3 | 2 hari |
| 11.7 | Evaluasi material: inventory days, shortage cost, holding cost rinci | 11.4, 11.6 | 1,5 hari |
| 11.8 | Orkestrator pipeline `POST /forecast/runs/{id}/plan` + frontend + export | semua | 3 hari |

Jalur kritis minimum untuk bab hasil thesis: **11.0 → 11.2 → 11.3 → 11.4 → 11.5 → 11.6 → 11.7**.

**Test fixture wajib:** gunakan 6 SKU + BOM dari sheet *Pengumpulan Data* dan deret 2024–2025 dari *Bab I Plan vs Forecast*, lalu verifikasi manual di Excel untuk: EOQ klasik 1 material, SS/ROP 1 material (bulanan → harian), stock akhir & utilisasi 1 periode, shortage cost 1 SKU.

---

## 8. Dokumen yang Harus Diperbarui

| Dokumen | Perubahan |
|---|---|
| `docs/RECONCILIATION.md` | Bab baru "Rekonsiliasi v3.2 — Alur Sistem Thesis (26 Okt 2026)": catat pembalikan sebagian keputusan 24 Agustus (kapasitas), revisi keputusan #16 (`current_stock`), EOQ klasik vs dinamis, bug SS/ROP |
| `docs/PRD.md` | FR-5 (EOQ klasik, buffer rasio), FR-6 (kapasitas material + stok + utilisasi), FR-7 (shortage cost, inventory days), FR-3 (α grid, feature importance, grid search); tambah FR-12 Stok & Kedatangan |
| `docs/ARCHITECTURE.md` | §4 data model (§4 dokumen ini), §5 API, §6.4 engine ES, §6.7 kapasitas, §6.8 EOQ klasik, env baru |
| `AGENTS.md` | §4 error code baru; checklist PR: konversi satuan periode ↔ hari wajib dites |
| `docs/TASK_BREAKDOWN.md` | Tambah Fase 11.0–11.8 |
| `Simulasi Thesis 2.xlsx` | Perbaiki `#REF!` baris 2025 tabel gap (angka 26%/33% di PRD bergantung ke sini); perbaiki penomoran tabel Penelitian Terdahulu; isi data Kapasitas Gudang material |

### Env baru

```env
# Semua di bawah DIBATALKAN sebagai env — menjadi master data Pengaturan Forecast (permintaan user)
EOQ_METHOD=classic                    # classic | dynamic
ES_ALPHA_GRID=0.01,0.05,0.15,0.2,0.8,0.95,0.99
ES_ALPHA_METRIC=mad
# FORECAST_RANKING_METRIC → dibatalkan: master data forecast_settings (Fase 11.2a)
SERVICE_LEVEL_PCT=95                  # ganti SERVICE_LEVEL_Z
ML_GRID_SEARCH=true
WAREHOUSE_CAPACITY_TARGET=material    # product | material | both
```