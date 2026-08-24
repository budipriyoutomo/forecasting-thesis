# Product Requirements Document (PRD)
## ForecastIQ — ML Forecasting, Inventory Decision & Warehouse Capacity Constraint (Produk Minuman RTD)

| | |
|---|---|
| **Product Owner** | Budi |
| **Dokumen** | PRD v3.0 (pivot — implementasi metodologi Thesis Noviana Asmoro) |
| **Tanggal** | 4 Agustus 2026 (sync dengan kode per Fase Migrasi 0–9) |
| **Status** | Implemented — Fase Migrasi 0–9 selesai & merged ke `main` |

> **Catatan versi:** v3.0 menggantikan v2.0 (raw material + klasifikasi ADI/CV² + ETS/ARIMA/LightGBM/Croston). Objek forecasting kini **produk jadi (SKU minuman RTD)** dengan kebutuhan raw material diturunkan lewat **BOM**, pemilihan metode lewat **Comparative Selection** (bandingkan semua metode, bukan klasifikasi kuadran), plus tiga modul baru: **EOQ & total biaya persediaan**, **validasi kapasitas gudang**, dan **evaluasi kinerja inventory**. Alasan pivot ada di `RECONCILIATION.md` §"Rekonsiliasi v3.0"; keputusan migrasi kode existing di §"Rekonsiliasi v3.1".
>
> Delta terhadap v2.0 ditandai inline: **[NEW]** fitur baru, **[CHANGED]** perilaku berubah, **[DROPPED]** tidak lagi di jalur aktif.

---

## 1. Latar Belakang & Masalah

Tim PPIC (Production Planning & Inventory Control) saat ini menentukan kebutuhan raw material dan level stok inventory secara manual (Excel), berdasarkan intuisi/rata-rata sederhana dari pemakaian bulan-bulan sebelumnya. Pendekatan ini menimbulkan beberapa masalah:

- Stok raw material sering **kehabisan (stockout)** saat demand naik tiba-tiba, menyebabkan produksi terhenti.
- Stok **menumpuk berlebih (overstock)** saat demand turun, mengikat cash dan menambah biaya gudang.
- Konsumsi raw material sering **tidak beraturan (intermittent/lumpy)** — bukan pola harian yang mulus seperti penjualan retail — sehingga metode forecasting sederhana (rata-rata) sering meleset jauh.
- Tidak ada visibilitas standar tentang kapan harus melakukan reorder dan berapa jumlahnya.
- Perhitungan manual di Excel rentan human error dan tidak scalable untuk banyak item material.
- Planner tidak punya cara sistematis untuk mempercayai (atau mengoreksi) angka forecast — keputusan akhir tetap butuh judgment manusia, tapi tanpa jejak/alasan yang tercatat.

**[CHANGED]** Dua masalah tambahan yang jadi fokus v3.0:

- Perusahaan sudah punya angka **Forecast eksisting** dan **Planning** sendiri, tapi tidak punya cara membuktikan apakah metode baru lebih akurat dari yang dipakai sekarang.
- Rekomendasi pengadaan sering **tidak muat secara fisik di gudang** — jumlah ekonomis (EOQ) dihitung tanpa memperhatikan kapasitas gudang yang tersedia, sehingga rekomendasi tidak bisa dieksekusi apa adanya.

**ForecastIQ** dibangun untuk mengotomatisasi prediksi demand **produk jadi**, menurunkannya jadi kebutuhan raw material via **BOM**, lalu mengubahnya jadi keputusan pengadaan (safety stock, buffer stock, EOQ) yang **tervalidasi terhadap kapasitas gudang** dan **terukur total biayanya** — dengan mesin seleksi model otomatis (**Comparative Selection**) yang membandingkan seluruh metode aktif, menjelaskan *mengapa* metode itu menang dalam bahasa natural, dan tetap memberi planner kendali penuh untuk override dengan audit trail.

**Value proposition inti:** bukan sekadar "menjalankan forecast", tapi rantai keputusan utuh **demand → material → pesanan ekonomis → muat di gudang → berapa hemat biayanya**, dengan pemilihan metode yang **bisa dipercaya & dijelaskan** ke user non-teknis.

## 2. Tujuan Produk

1. **[CHANGED]** Memprediksi demand **produk jadi** (SKU) untuk periode mendatang (bulanan) berdasarkan data historis, dengan metode yang dipilih otomatis lewat perbandingan akurasi seluruh metode aktif.
2. **[NEW]** Menurunkan hasil forecast produk menjadi **kebutuhan raw material** melalui BOM (Bill of Material).
3. **[CHANGED]** Memberikan rekomendasi **safety stock**, **buffer stock**, **reorder point**, dan **EOQ (jumlah pesanan ekonomis)** per item material.
4. **[NEW]** Memvalidasi apakah forecast produk **muat kapasitas gudangnya**, per produk (kapasitas isian bebas planner — **[CHANGED 24 Agustus 2026]** bukan turunan luas gudang × dimensi palet).
5. **[NEW]** Mengukur **total biaya persediaan (TIC)** usulan sistem dibanding baseline perusahaan, dan melaporkan **% penghematan**.
6. **[NEW]** Mengevaluasi **kinerja inventory** (service level, fill rate, stock out rate, inventory turnover) untuk skenario baseline vs ForecastIQ.
7. Menjelaskan hasil forecast dalam bahasa natural (bukan angka statistik mentah) agar planner non-teknis memahami dasar keputusan sistem.
8. Memberikan planner kemampuan **override** rekomendasi sistem, dengan alasan & jejak audit yang tercatat penuh.
9. Memberikan visibilitas (dashboard) tentang tren demand, akurasi forecast, biaya, dan status stok.
10. Mengurangi waktu yang dibutuhkan tim PPIC untuk menyiapkan rencana pengadaan, dari manual Excel menjadi otomatis.

## 3. Target Pengguna

| Peran | Kebutuhan Utama |
|---|---|
| Staff/Supervisor PPIC (Planner) | Upload data historis, menjalankan forecast produk, melihat rekomendasi order, override jika perlu |
| Tim Purchasing | Melihat rekomendasi reorder, EOQ, & jumlah pengadaan per material |
| Manajer Produksi/Supply Chain | Melihat dashboard ringkasan, tren, akurasi forecast, **[NEW]** total biaya persediaan & metrik kinerja inventory, dan riwayat override untuk pengambilan keputusan |
| Admin | Mengelola master data **produk, material, dan BOM**, user, **[NEW]** konfigurasi kapasitas gudang per produk, dan konfigurasi sistem (engine aktif, metrik ranking) |

## 4. Lingkup (Scope)

### 4.1 Dalam Lingkup (In-Scope) — MVP
- **[CHANGED]** Upload data historis demand **produk jadi** via file **CSV/Excel**, dengan **tiga seri paralel per SKU per periode**: `forecast_existing` (angka forecast perusahaan saat ini), `planning` (rencana produksi), dan `actual` (realisasi). Tiga kolom ini yang memungkinkan sistem membuktikan peningkatan akurasi dibanding metode existing.
- Validasi & pembersihan data (deteksi kolom wajib, format tanggal, nilai kosong/anomali) sebelum diproses.
- **[CHANGED]** Master data **produk** (kode SKU, nama), **material** (kode, nama, satuan, kategori, lead time supplier, MOQ, **[NEW]** dimensi fisik), dan **[NEW] BOM** (produk → material, qty per unit).
- **[CHANGED]** **Comparative Selection Engine**: jalankan **seluruh** metode aktif untuk tiap SKU, hitung MAD/MFE/MSE/MAPE tiap metode via backtest, pilih metode dengan metrik ranking terbaik. Tanpa klasifikasi kuadran demand.
- **Penjelasan bahasa natural** untuk setiap hasil forecast (metode apa yang dipilih dan mengapa).
- **[NEW] BOM breakdown**: forecast produk × BOM → kebutuhan raw material per periode.
- **[CHANGED]** Perhitungan **safety stock**, **[NEW] buffer stock**, **reorder point**, dan **[NEW] EOQ dinamis** per item material berdasarkan hasil forecast, lead time, MOQ, dan service level yang dikonfigurasi.
- **[NEW] Validasi kapasitas gudang**: kapasitas per produk (isian bebas planner) dibandingkan dengan total qty forecast produk itu — tampil sebagai flag non-blocking, per produk.
- **[NEW] Total biaya persediaan (TIC)**: ordering cost + holding cost, usulan ForecastIQ vs baseline perusahaan, beserta % penghematan.
- **[NEW] Evaluasi kinerja inventory**: service level, fill rate, stock out rate, inventory turnover — dihitung untuk dua skenario (baseline & ForecastIQ).
- **[CHANGED]** **Planner override**: planner dapat mengubah manual hasil forecast atau rekomendasi reorder; wajib menyertakan alasan, tersimpan sebagai revisi (bukan overwrite) dengan audit trail lengkap.
- Dashboard visualisasi: tren aktual vs forecast, status stok per item, daftar item yang perlu segera di-reorder, riwayat override, **[NEW]** ringkasan biaya & metrik inventory, **[NEW]** indikator kapasitas gudang.
- Export hasil forecast & rekomendasi reorder ke Excel/PDF.
- Manajemen user dasar (login, role: Admin/PPIC/Purchasing/Viewer).
- Riwayat/audit trail lengkap: batch upload, hasil forecast per run, dan override.

> **[DROPPED]** Klasifikasi pola demand ADI/CV² (kuadran smooth/erratic/intermittent/lumpy) dan weighted scoring (MASE + guardrail + kecocokan kuadran) **tidak lagi dipakai di jalur aktif**. Kodenya dipertahankan di `backend/app/services/forecasting/legacy/` (tidak dipanggil) sebagai referensi — lihat `RECONCILIATION.md` §Keputusan Terbuka v3.0 poin 2. **[DROPPED]** Jalur forecasting raw material langsung (poin 1) dilepas 4 Agustus 2026: tabel `consumption_history` di-drop dan ingestion hanya menerima `product_code`.

### 4.2 Di Luar Lingkup (Out of Scope) — MVP
- Integrasi langsung ke sistem ERP/database perusahaan (real-time sync) — direncanakan untuk versi berikutnya.
- Multi-tenant/multi-perusahaan (konsep "organization/project" terpisah) — MVP diasumsikan 1 perusahaan/instance.
- Optimasi multi-supplier / negosiasi harga otomatis.
- **[NEW]** Racking/penyimpanan bertingkat di gudang — kapasitas dihitung berbasis footprint lantai saja (`WAREHOUSE_PALLET_NO_RACKING=true`), sesuai batasan masalah thesis.
- Aplikasi mobile native (MVP berbasis web responsive).
- Notifikasi otomatis via WhatsApp/email (fase lanjutan).
- Async job processing (Celery/Redis) — MVP synchronous, ditambahkan hanya jika ada sinyal kebutuhan nyata (volume/waktu proses).

## 5. Functional Requirements

**[NEW]** Alur utama v3.0, untuk membaca urutan FR di bawah:

```
upload demand produk (FR-1) → forecast produk (FR-3)   ← hasil forecast berhenti di sini
  → reorder + buffer + EOQ (FR-4, pakai BOM di memori) → validasi kapasitas gudang (FR-10)
  → TIC & metrik kinerja inventory (FR-11) → dashboard (FR-6) / export (FR-7)
```

Planner override (FR-5) dapat menyentuh dua titik dalam alur ini: hasil forecast dan rekomendasi reorder. (Titik ketiga, kebutuhan material, dihapus 24 Agustus 2026 — lihat FR-9.)

### FR-1 Data Ingestion
- FR-1.1 **[CHANGED]** User dapat mengupload file CSV/Excel berisi data historis demand produk jadi. Kolom wajib: `product_code`, `period`, `actual`; ditambah dua seri opsional `forecast_existing` dan `planning` yang dipakai sebagai pembanding baseline. **[DROPPED]** Format lama berbasis `material_code` **tidak lagi diterima** — upload raw material langsung dilepas dari scope v3.0 (keputusan 4 Agustus 2026, lihat `RECONCILIATION.md`).
- FR-1.2 Sistem memvalidasi format file dan menampilkan error yang jelas jika format tidak sesuai (kolom hilang, tipe data salah, dsb) — sebelum data dipakai untuk forecast.
- FR-1.3 Sistem menampilkan preview data (beberapa baris pertama) sebelum diproses, agar user bisa mengecek hasil parsing.
- FR-1.4 Setiap upload disimpan sebagai `upload_session` dengan riwayat (siapa upload, kapan, jumlah baris, jumlah produk/material terdeteksi).
- FR-1.5 File upload disimpan sementara (temp storage, TTL 1 jam) sampai divalidasi, lalu dipindah ke penyimpanan permanen jika valid.

### FR-2 Master Data: Produk, Material & BOM
- FR-2.1 CRUD master data material: kode, nama, kategori, satuan, lead time supplier (hari), minimum order quantity (MOQ), safety stock manual (opsional override), **[NEW]** dimensi fisik material.
- FR-2.2 Import master data material via Excel/CSV.
- FR-2.3 **[NEW]** CRUD + import master data **produk** (SKU): kode unik, nama. Kode duplikat ditolak dengan `PRODUCT_CODE_EXISTS`.
- FR-2.4 **[NEW]** CRUD + import **BOM**: relasi produk → material dengan qty per unit produk. Referensi produk/material yang tidak ada ditolak dengan `BOM_NOT_FOUND`.

### FR-3 Comparative Selection Engine
> **[CHANGED]** Seluruh FR-3 ditulis ulang. v2.0 memilih metode lewat klasifikasi kuadran + weighted scoring; v3.0 membandingkan langsung akurasi seluruh metode aktif. FR-3.1–3.4 dan FR-3.6 versi v2.0 **[DROPPED]**.

- FR-3.1 **[CHANGED]** Untuk tiap produk, sistem menjalankan **seluruh** metode forecasting yang aktif (tanpa penyaringan berdasarkan pola demand lebih dulu).
- FR-3.2 **[CHANGED]** Tiap metode menjalankan holdout backtest dan melaporkan empat metrik akurasi: **MAD, MFE, MSE, MAPE**. MASE dihitung sebagai metrik tambahan opsional (`COMPUTE_MASE`), tidak dipakai untuk ranking.
- FR-3.3 **[CHANGED]** Sistem memilih metode dengan nilai **metrik ranking terendah** (`FORECAST_RANKING_METRIC`, default `mape`; opsi lain `mad`/`mse`/`mfe_abs`). Metode yang metriknya tidak terdefinisi diperlakukan sebagai terburuk, bukan menggagalkan run.
- FR-3.4 **[NEW]** Seluruh metode yang berhasil dievaluasi disimpan di `candidates_evaluated` (metode + keempat metrik) **dan ditampilkan di UI** sebagai tabel terurut dari metrik ranking terbaik, dengan pemenang ditandai — agar user bisa menilai apakah selisih akurasinya berarti, bukan hanya menerima pemenangnya.
- FR-3.5 **[CHANGED]** Sistem menghasilkan penjelasan bahasa natural tentang metode yang dipilih dan alasannya. Di mode otomatis penjelasan **dibuka dengan dasar pemilihannya** — metode pemenang, berapa metode dibandingkan, metrik ranking beserta nilainya, dan metode terbaik berikutnya — baru diikuti karakteristik metode tersebut. Di mode manual tidak ada narasi perbandingan (tidak ada yang dibandingkan).
- FR-3.6 **[CHANGED]** Metode yang gagal saat fit/backtest di mode otomatis **dikecualikan dari perbandingan** dan run tetap lanjut dengan metode yang tersisa. Jika **semua** metode gagal → `MODEL_SELECTION_FAILED`. (Fallback berurutan versi v2.0 tidak berlaku — tidak ada urutan skor untuk di-fallback-i.)
- FR-3.7 User dapat melihat metode yang dipakai per item dan (opsional) memicu ulang forecast dengan metode berbeda secara manual.
- FR-3.8 **[CHANGED]** Daftar metode aktif (`FORECAST_ENGINES_ENABLED`) dan metrik ranking (`FORECAST_RANKING_METRIC`) dapat dikonfigurasi tanpa mengubah kode.
- FR-3.9 **[CHANGED]** **Sebelum menjalankan forecast** (belum generate), user dapat memilih mode: **"Bandingkan Otomatis (Direkomendasikan)"** — sistem membandingkan seluruh metode aktif — atau **memilih metode secara manual** dari daftar metode yang tersedia (Moving Average / Exponential Smoothing / Random Forest / XGBoost / LSTM) untuk run tersebut.
- FR-3.10 **[CHANGED]** Jika user memilih metode manual, sistem **langsung memakai metode itu** (tanpa perbandingan), tapi tetap menjalankan backtest untuk melaporkan MAD/MFE/MSE/MAPE dan tetap menghasilkan penjelasan bahasa natural — supaya user tetap tahu seberapa akurat pilihannya secara historis.
- FR-3.11 Jika metode manual yang dipilih gagal dijalankan (mis. data tidak cukup untuk metode itu), sistem mengembalikan error yang jelas (`UNSUPPORTED_FORECAST_METHOD` atau `MODEL_SELECTION_FAILED`), bukan diam-diam pindah ke metode lain — karena user sudah memilih secara sadar.

### FR-4 Rekomendasi Reorder, Buffer Stock & EOQ
- FR-4.1 Sistem menghitung safety stock berdasarkan variabilitas demand, lead time, dan target service level (dapat dikonfigurasi, `SERVICE_LEVEL_Z` default 1.65 ≈ 95%).
- FR-4.2 Sistem menghitung reorder point = (demand rata-rata selama lead time) + safety stock.
- FR-4.3 Sistem menghasilkan rekomendasi jumlah order (order quantity) mempertimbangkan MOQ sebagai batas bawah.
- FR-4.4 Sistem menandai item dengan status "Perlu Reorder Segera", "Aman", atau "Overstock".
- FR-4.5 **[NEW]** Sistem menghitung **buffer stock** = Standar Pemakaian − Aktual Pemakaian (tidak negatif), di mana Standar Pemakaian = Output Produksi × BOM — untuk mengantisipasi waste produksi.
- FR-4.6 **[NEW]** Sistem menghitung **EOQ dinamis** dengan mencari jumlah siklus pemesanan yang meminimalkan total biaya `TC = nS + Σ(Iₜ × H)`, lalu membulatkan ke kelipatan MOQ.
- FR-4.7 **[NEW]** Tiap rekomendasi menyimpan komponen biayanya: `ordering_cost`, `holding_cost`, dan `total_inventory_cost`.
- FR-4.8 **[CHANGED]** Rekomendasi digenerate lewat `POST` dengan `current_stock` dikirim sebagai parameter request (bukan kolom tersimpan), lalu bisa dibaca ulang lewat `GET`.

### FR-5 Planner Override & Audit Trail
- FR-5.1 **[CHANGED]** Planner dapat override manual hasil forecast atau rekomendasi reorder untuk item tertentu. ~~kebutuhan material hasil BOM breakdown (`material_requirement`)~~ **[REMOVED 24 Agustus 2026]** — hasil forecast berhenti di level produk, target override itu ikut dihapus (lihat FR-9).
- FR-5.2 Setiap override wajib menyertakan alasan (tidak boleh kosong — ditolak dengan error jika kosong).
- FR-5.3 Override disimpan sebagai revisi baru (append-only), tidak menghapus/menimpa hasil sistem asli.
- FR-5.4 Riwayat override (siapa, kapan, nilai sebelum/sesudah, alasan) dapat dilihat kembali oleh Admin/Manajer.

### FR-6 Dashboard & Visualisasi
- FR-6.1 **[CHANGED]** Dashboard ringkasan: jumlah item perlu reorder, akurasi forecast rata-rata (**MAPE**, bukan lagi MASE), tren demand total, **[NEW]** total biaya persediaan run terakhir, **[NEW]** indikator kapasitas gudang, **[NEW]** ringkasan metrik inventory per skenario.
- FR-6.2 Grafik tren aktual vs forecast per item, termasuk confidence interval (lower/upper).
- FR-6.3 Tabel status stok seluruh item dengan filter/sort (kategori, status, urgensi).
- FR-6.4 Tampilan riwayat override per item.
- FR-6.5 **[NEW]** Widget ringkasan biaya (TIC usulan vs baseline + % penghematan) dan tabel metrik kinerja inventory, tampil di halaman hasil forecast setelah rekomendasi reorder dihitung.

### FR-7 Export & Laporan
- FR-7.1 Export hasil forecast & rekomendasi reorder ke Excel. **[NEW]** Kolom `buffer_stock`, `eoq_qty`, `ordering_cost`, `holding_cost`, `total_inventory_cost` ditambahkan **setelah** kolom lama, agar file yang sudah dipakai downstream tidak berubah posisi kolomnya.
- FR-7.2 Export laporan ringkasan ke PDF.

### FR-8 User Management
- FR-8.1 Login dengan role: Admin, PPIC (Planner), Purchasing, Viewer.
- FR-8.2 Role menentukan akses (mis. Purchasing hanya bisa lihat rekomendasi reorder, tidak bisa override atau ubah master data). Akses yang ditolak karena role mengembalikan `AUTH_FORBIDDEN` (403).

### FR-9 BOM Breakdown & Kebutuhan Material **[REMOVED 24 Agustus 2026]**
> **Dibatalkan.** Hasil forecast adalah **produk**, titik — tidak ada entitas kebutuhan material yang tersimpan per run. Tabel `material_requirements`, endpoint `GET /forecast/runs/{run_id}/material-requirements`, dan target override `material_requirement` dihapus (lihat `RECONCILIATION.md` §"Forecast produk-only").

- ~~FR-9.1 Sistem menurunkan hasil forecast produk menjadi kebutuhan raw material per periode.~~ **[REMOVED]**
- ~~FR-9.2 Hasil breakdown disimpan sebagai `material_requirements` per forecast run.~~ **[REMOVED]**
- ~~FR-9.3 Produk tanpa BOM: forecast tetap tersimpan, breakdown dilewati.~~ **[REMOVED]** — tidak relevan lagi karena forecast tak pernah menyentuh BOM.

> BOM tetap ada sebagai **master data** dan tetap dipakai FR-4 (reorder/EOQ) & FR-11 (biaya) lewat perhitungan di memori, bukan lewat tabel turunan per run.

### FR-10 Validasi Kapasitas Gudang **[NEW, redesain 24 Agustus 2026]**
- FR-10.1 Admin dapat mengatur kapasitas gudang **per produk**: satu baris per produk, `capacity_qty` diisi bebas oleh planner (unit sama dengan unit produk) — **bukan** diturunkan dari luas gudang atau dimensi palet. Satu produk maksimal satu baris (`WAREHOUSE_CONFIG_EXISTS` bila duplikat). Setiap baris juga punya `uom` (satuan) isian bebas teks — **tidak ada tabel master UOM**.
- FR-10.2 Sistem membandingkan, per produk yang dikonfigurasi: kebutuhan = total qty forecast produk itu di satu run, terhadap `capacity_qty` konfigurasinya.
- FR-10.3 Produk tanpa konfigurasi kapasitas, atau tanpa forecast COMPLETED di run itu, dilewati (tak bisa dibandingkan) — tidak menggagalkan validasi produk lain.
- FR-10.4 Hasil validasi tampil sebagai **flag non-blocking**, per produk (muat / tidak muat) di halaman hasil forecast — sistem tidak menolak rekomendasi, hanya memberi peringatan agar planner bisa menyesuaikan. Flag agregat run = True hanya bila SEMUA produk yang dibandingkan muat.
- FR-10.5 Belum ada konfigurasi kapasitas sama sekali menghasilkan `WAREHOUSE_CONFIG_NOT_FOUND`, bukan diam-diam memakai angka default.

### FR-11 Total Biaya & Evaluasi Kinerja Inventory **[NEW]**
- FR-11.1 Sistem menghitung **TIC (Total Inventory Cost)** = ordering cost + holding cost, untuk dua skenario: **usulan ForecastIQ** (dari rekomendasi tersimpan) dan **baseline perusahaan** (dari seri `planning`, lewat jalur BOM → EOQ yang sama agar perbandingannya simetris).
- FR-11.2 Sistem melaporkan **% penghematan** = (TIC baseline − TIC usulan) ÷ TIC baseline × 100.
- FR-11.3 Sistem menghitung empat metrik kinerja inventory per skenario (`baseline` dan `forecastiq`): **service level** (α, berbasis siklus), **fill rate** (β), **stock out rate**, dan **inventory turnover**.
- FR-11.4 Definisi rumus keempat metrik tidak tersedia di sumber thesis; definisi standar yang dipakai disepakati bersama user dan dicatat di `RECONCILIATION.md` §Fase 7 agar bisa dipertanggungjawabkan.

## 6. Metode Forecasting yang Didukung

**[CHANGED]** Daftar metode diganti total mengikuti Bab III thesis: dua baseline konvensional + tiga metode machine learning, semuanya dibandingkan secara langsung.

| Kategori | Metode | Catatan | Status |
|---|---|---|---|
| Baseline konvensional | Moving Average | Window dikonfigurasi (`MOVING_AVERAGE_WINDOW`, default 3) | MVP |
| Baseline konvensional | Exponential Smoothing | Pembanding klasik untuk metode ML | MVP |
| Machine Learning | Random Forest | Regressor atas fitur lag | MVP |
| Machine Learning | XGBoost | Regressor atas fitur lag | MVP |
| Machine Learning | LSTM | Butuh histori lebih panjang (`LSTM_MIN_PERIODS`, default 24) dan TensorFlow | MVP — **belum terverifikasi jalan di image Docker**, lihat `TASK_BREAKDOWN.md` §10 |
| **[DROPPED]** Legacy v2.0 | ETS, ARIMA, LightGBM, Croston/SBA, Prophet | Dipindah ke `engines/legacy/`, nonaktif di `FORECAST_ENGINES_ENABLED`. **Tidak dihapus** — kandidat reuse untuk forecasting raw material intermittent di luar scope thesis | Nonaktif |
| Post-MVP | SARIMA, Holt-Winters, Theta, TBATS, N-HiTS, TFT | Musiman kompleks / long-horizon multivariate | Post-MVP |

Sistem menjalankan **seluruh metode aktif** untuk tiap SKU, menghitung **MAD/MFE/MSE/MAPE** lewat backtest, lalu memilih metode dengan metrik ranking terendah — bukan satu metode yang dipaksakan untuk semua item, dan bukan pula penyaringan kandidat berdasarkan klasifikasi pola demand lebih dulu.

> **Konsekuensi biaya komputasi [CHANGED]:** menjalankan semua metode selalu lebih mahal daripada menyaring kandidat dulu seperti v2.0. Ini trade-off yang disengaja — metodologi thesis menuntut perbandingan langsung antar metode agar klaim akademiknya bisa dipertanggungjawabkan. Timeout per engine (`ENGINE_TIMEOUT_SECONDS` 45 detik; LSTM 120 detik) yang menjaga satu metode lambat tidak memblokir seluruh run.

## 7. Non-Functional Requirements

- **Usability**: Interface mudah digunakan oleh staff PPIC yang terbiasa dengan Excel; hasil forecast disertai penjelasan bahasa natural, bukan hanya angka statistik.
- **Performance**: **[CHANGED]** Forecasting run untuk ratusan SKU selesai dalam hitungan detik–menit; timeout per engine (`ENGINE_TIMEOUT_SECONDS` 45 detik, `LSTM_ENGINE_TIMEOUT_SECONDS` 120 detik) dan timeout run (`FORECAST_TIMEOUT_SECONDS` 180 detik) agar satu item/metode bermasalah tidak memblokir seluruh run.
- **Reliability**: Validasi data ketat; kegagalan satu engine tidak boleh menggagalkan seluruh proses seleksi (exclude & lanjut dengan metode yang tersisa). **[NEW]** Produk tanpa BOM tidak menggagalkan forecast run — breakdown material untuk produk itu saja yang dilewati.
- **Security**: Autentikasi JWT (Supabase Auth), role-based access control, file upload divalidasi (tipe, ukuran maksimum).
- **Scalability**: Registry/Factory pattern untuk model engine — metode baru bisa ditambah tanpa mengubah orchestrator/endpoint/test yang sudah ada.
- **Auditability**: Setiap upload, forecast run, dan override tercatat lengkap (siapa, kapan, versi data, alasan).
- **Data & Model Integrity**: Data historis asli tidak pernah dimodifikasi secara silent; hasil forecast/override tidak pernah di-overwrite, selalu sebagai entri baru.
- **Testability**: **[CHANGED]** Seluruh logic inti (metrik evaluasi, tiap engine, reorder/EOQ, kapasitas gudang, TIC, metrik inventory) dikembangkan dengan TDD dan coverage minimum sesuai `AGENTS.md`. Rumus yang punya konsekuensi angka (EOQ, TIC, kapasitas gudang per produk, 4 metrik inventory) diverifikasi manual di test, bukan hanya di-snapshot.

## 8. Asumsi & Batasan

- Data historis minimal 12 periode (`BACKTEST_MIN_PERIODS`, default 12) agar backtesting bermakna; di bawah itu → error `INSUFFICIENT_DATA` sebelum backtest dijalankan (fail fast). **[NEW]** LSTM menuntut minimal 24 periode (`LSTM_MIN_PERIODS`).
- **[NEW]** Periode data adalah **bulanan** (mengikuti data thesis), bukan harian.
- Format file upload mengikuti template kolom wajib yang disediakan sistem.
- **[NEW]** Kapasitas gudang dihitung berbasis **footprint lantai tanpa racking** (`WAREHOUSE_PALLET_NO_RACKING=true`) — penyimpanan bertingkat tidak diperhitungkan, sesuai batasan masalah thesis.
- **[NEW]** `DEFAULT_ORDERING_COST` dan `DEFAULT_HOLDING_COST_RATE` default 0 — angka biaya riil harus diisi user, jika tidak maka TIC & EOQ tidak bermakna secara ekonomis (hasilnya nol, bukan salah).
- **[NEW]** Baseline pembanding adalah seri `planning` perusahaan; kalau kolom itu tidak diisi saat upload, perbandingan TIC dan metrik inventory skenario `baseline` tidak bisa dihitung.
- MVP tidak terhubung real-time ke ERP — proses berbasis upload manual berkala.
- MVP diasumsikan 1 perusahaan/instance (bukan multi-tenant SaaS) — lihat "Keputusan Terbuka" di `RECONCILIATION.md`.
- Forecasting dijalankan synchronous untuk MVP; async processing (Celery/Redis) hanya ditambahkan jika ada sinyal kebutuhan nyata.

## 9. Metrik Keberhasilan (Success Metrics)

- **[NEW]** **Akurasi ForecastIQ lebih baik daripada forecast eksisting perusahaan** — MAPE metode terpilih dibandingkan langsung dengan MAPE kolom `forecast_existing` atas `actual` yang sama. Ini metrik keberhasilan utama v3.0 karena jadi klaim inti thesis.
- **[NEW]** **% penghematan total biaya persediaan** (TIC usulan vs TIC baseline) positif dan konsisten lintas periode.
- **[NEW]** Seluruh rekomendasi pengadaan **muat dalam kapasitas gudang** — jumlah run dengan flag "tidak muat" menurun setelah planner menyesuaikan.
- **[CHANGED]** Metrik kinerja inventory skenario ForecastIQ lebih baik dari baseline: service level & fill rate naik, stock out rate turun, inventory turnover membaik.
- Pengurangan kejadian stockout raw material minimal 30% dalam 3 bulan penggunaan.
- Pengurangan waktu penyusunan rencana pengadaan dari manual Excel (berjam-jam) menjadi < 30 menit.
- Tingkat kepercayaan planner terhadap sistem (diukur dari frekuensi override — target: override menurun seiring waktu karena planner makin percaya, bukan karena dipaksa).

## 10. Contoh User Stories

1. **[CHANGED]** Sebagai **Planner PPIC**, saya ingin mengupload data demand produk bulan lalu (banyak SKU sekaligus, berikut angka forecast & planning yang kami pakai sekarang) dalam satu file CSV, agar sistem otomatis memproses forecast tanpa saya hitung manual per item **dan bisa menunjukkan apakah hasilnya lebih akurat dari cara kami sekarang**.
2. Sebagai **Planner PPIC**, saya ingin melihat preview & validasi data sebelum diproses, agar saya bisa memperbaiki data yang salah lebih dulu.
3. Sebagai **Planner PPIC**, saya ingin membaca penjelasan bahasa natural kenapa sistem memilih metode tertentu untuk suatu item, agar saya bisa menilai apakah masuk akal sebelum dipakai untuk keputusan pengadaan.
4. Sebagai **Planner PPIC**, saya ingin bisa override rekomendasi sistem untuk item tertentu (mis. karena ada informasi dari lapangan yang sistem tidak tahu), dengan mencatat alasannya.
5. Sebagai **Tim Purchasing**, saya ingin melihat daftar material yang perlu segera di-reorder beserta jumlah rekomendasinya, agar saya bisa langsung membuat PO.
6. Sebagai **Manajer**, saya ingin melihat dashboard akurasi forecast dan riwayat override, agar saya bisa menilai keandalan sistem dan pola judgment planner dari waktu ke waktu.
7. **[CHANGED]** Sebagai **Admin**, saya ingin mengatur lead time & MOQ per material, BOM per produk, **[NEW]** kapasitas gudang per produk (angka bebas), serta daftar metode aktif dan metrik ranking, agar perhitungan reorder point, kapasitas, dan pemilihan model sesuai kondisi riil.
8. **[CHANGED]** Sebagai **Planner PPIC**, saya ingin bisa memilih sendiri metode forecasting (mis. paksa pakai XGBoost) sebelum generate, karena saya sudah tahu dari pengalaman metode mana yang biasanya cocok untuk item tertentu — tanpa harus menunggu hasil perbandingan otomatis dulu baru override.
9. **[NEW]** Sebagai **Planner PPIC**, saya ingin melihat kebutuhan raw material yang otomatis diturunkan dari forecast produk lewat BOM, agar saya tidak perlu menghitung sendiri berapa bahan yang dibutuhkan untuk memenuhi rencana produksi.
10. **[NEW]** Sebagai **Manajer Gudang**, saya ingin diperingatkan kalau rekomendasi pengadaan tidak muat di gudang, agar saya bisa menyesuaikan jadwal pengiriman sebelum barang terlanjur datang dan menumpuk di lorong.
11. **[NEW]** Sebagai **Manajer Supply Chain**, saya ingin melihat berapa total biaya persediaan usulan sistem dibanding cara kami sekarang, agar saya punya angka konkret untuk membenarkan perubahan cara kerja ke manajemen.
12. **[NEW]** Sebagai **Planner PPIC**, saya ingin melihat metrik mana saja yang dipakai membandingkan kelima metode dan berapa nilainya, agar saya bisa menilai apakah selisih akurasinya cukup berarti — bukan sekadar menerima "sistem memilih X".

## 11. Roadmap Setelah MVP (Future Considerations)

- Integrasi langsung ke ERP/database perusahaan (real-time atau scheduled sync).
- Notifikasi otomatis (email/WhatsApp) saat item mencapai reorder point.
- **[NEW]** Jalur forecasting raw material langsung (untuk perusahaan tanpa BOM lengkap, atau item berpola intermittent) — dilepas dari v3.0 pada 4 Agustus 2026. Menghidupkannya lagi **bukan sekadar mengubah `FORECAST_ENGINES_ENABLED`**: butuh tabel histori raw material baru (`consumption_history` sudah di-drop di `c9d0e1f2a3b4`), mode ingestion `material_code`, dan jalur forecast/reorder level material. Engine legacy di `legacy/` masih ada sebagai titik awal.
- **[NEW]** Racking / penyimpanan bertingkat dalam perhitungan kapasitas gudang.
- Multi-lokasi/gudang, multi-tenant (organization/project) untuk dijual sebagai SaaS ke banyak perusahaan.
- Engine tambahan: SARIMA, Holt-Winters, TBATS, NeuralProphet, dan tier enterprise (N-HiTS/TFT).
- Async job processing (Celery/Redis) bila volume data/waktu proses sudah menuntutnya.

**[DROPPED] dari roadmap — sudah terimplementasi di v3.0:** forecasting demand produk jadi + backward calculation via BOM (FR-3/FR-9), XGBoost & LSTM (§6).

---
*Dokumen ini adalah living document. Lihat `RECONCILIATION.md` untuk histori keputusan: §"Rekonsiliasi v3.0" untuk alasan pivot metodologi, §"Rekonsiliasi v3.1" untuk keputusan migrasi kode existing.*
