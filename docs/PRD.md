# Product Requirements Document (PRD)
## ForecastIQ — AI-Powered Raw Material & Inventory Forecasting Platform (PPIC)

| | |
|---|---|
| **Product Owner** | Budi |
| **Dokumen** | PRD v2.0 (merged dengan spesifikasi teknis ForecastIQ / AGENTS.md) |
| **Tanggal** | 23 Juli 2026 |
| **Status** | Draft — untuk direview sebelum development |

> **Catatan versi:** v2.0 menggabungkan draft awal "Tools Forecasting Raw Material PPIC" dengan visi **ForecastIQ** (auto model selection engine yang bisa dipercaya & dijelaskan, planner override dengan audit trail). Lihat `RECONCILIATION.md` untuk detail keputusan penggabungan.

---

## 1. Latar Belakang & Masalah

Tim PPIC (Production Planning & Inventory Control) saat ini menentukan kebutuhan raw material dan level stok inventory secara manual (Excel), berdasarkan intuisi/rata-rata sederhana dari pemakaian bulan-bulan sebelumnya. Pendekatan ini menimbulkan beberapa masalah:

- Stok raw material sering **kehabisan (stockout)** saat demand naik tiba-tiba, menyebabkan produksi terhenti.
- Stok **menumpuk berlebih (overstock)** saat demand turun, mengikat cash dan menambah biaya gudang.
- Konsumsi raw material sering **tidak beraturan (intermittent/lumpy)** — bukan pola harian yang mulus seperti penjualan retail — sehingga metode forecasting sederhana (rata-rata) sering meleset jauh.
- Tidak ada visibilitas standar tentang kapan harus melakukan reorder dan berapa jumlahnya.
- Perhitungan manual di Excel rentan human error dan tidak scalable untuk banyak item material.
- Planner tidak punya cara sistematis untuk mempercayai (atau mengoreksi) angka forecast — keputusan akhir tetap butuh judgment manusia, tapi tanpa jejak/alasan yang tercatat.

**ForecastIQ** dibangun untuk mengotomatisasi prediksi kebutuhan raw material/inventory berdasarkan data historis — dengan mesin seleksi model otomatis (**Auto Model Selection Engine**) yang memilih metode forecasting paling cocok per item material, menjelaskan *mengapa* metode itu dipilih dalam bahasa natural, dan tetap memberi planner kendali penuh untuk override dengan audit trail.

**Value proposition inti:** bukan sekadar "menjalankan forecast", tapi mesin seleksi model otomatis yang **akurat untuk pola demand yang tidak beraturan** (khas raw material) dan **bisa dipercaya & dijelaskan** ke user non-teknis.

## 2. Tujuan Produk

1. Memprediksi kebutuhan/konsumsi raw material untuk periode mendatang (mingguan/bulanan) berdasarkan data historis, dengan metode yang dipilih otomatis sesuai karakteristik pola demand tiap item.
2. Memberikan rekomendasi **reorder point** dan **safety stock** per item material.
3. Menjelaskan hasil forecast dalam bahasa natural (bukan angka statistik mentah) agar planner non-teknis memahami dasar keputusan sistem.
4. Memberikan planner kemampuan **override** rekomendasi sistem, dengan alasan & jejak audit yang tercatat penuh.
5. Memberikan visibilitas (dashboard) tentang tren pemakaian, akurasi forecast, dan status stok.
6. Mengurangi waktu yang dibutuhkan tim PPIC untuk menyiapkan rencana pengadaan, dari manual Excel menjadi otomatis.

## 3. Target Pengguna

| Peran | Kebutuhan Utama |
|---|---|
| Staff/Supervisor PPIC (Planner) | Upload data historis, menjalankan forecast, melihat rekomendasi order, override jika perlu |
| Tim Purchasing | Melihat rekomendasi reorder & jumlah pengadaan per material |
| Manajer Produksi/Supply Chain | Melihat dashboard ringkasan, tren, akurasi forecast, dan riwayat override untuk pengambilan keputusan |
| Admin | Mengelola master data material, user, dan konfigurasi sistem (bobot scoring, engine aktif) |

## 4. Lingkup (Scope)

### 4.1 Dalam Lingkup (In-Scope) — MVP
- Upload data historis pemakaian/konsumsi raw material via file **CSV/Excel** (satu file dapat berisi banyak material/SKU sekaligus).
- Validasi & pembersihan data (deteksi kolom wajib, format tanggal, nilai kosong/anomali) sebelum diproses.
- Master data material (kode item, nama, satuan, kategori, lead time supplier, minimum order quantity/MOQ).
- **Auto Model Selection Engine**: klasifikasi pola demand (ADI/CV² → smooth/erratic/intermittent/lumpy), backtesting multi-metode (MASE), weighted scoring, pemilihan model otomatis per material.
- **Penjelasan bahasa natural** untuk setiap hasil forecast (metode apa yang dipilih dan mengapa).
- Perhitungan **safety stock** dan **reorder point** per item berdasarkan hasil forecast, lead time, dan service level yang dikonfigurasi.
- **Planner override**: planner dapat mengubah manual hasil forecast/rekomendasi reorder, wajib menyertakan alasan, tersimpan sebagai revisi (bukan overwrite) dengan audit trail lengkap.
- Dashboard visualisasi: tren pemakaian aktual vs forecast, status stok per item, daftar item yang perlu segera di-reorder, riwayat override.
- Export hasil forecast & rekomendasi reorder ke Excel/PDF.
- Manajemen user dasar (login, role: Admin/PPIC/Purchasing/Viewer).
- Riwayat/audit trail lengkap: batch upload, hasil forecast per run, dan override.

### 4.2 Di Luar Lingkup (Out of Scope) — MVP
- Integrasi langsung ke sistem ERP/database perusahaan (real-time sync) — direncanakan untuk versi berikutnya.
- Multi-tenant/multi-perusahaan (konsep "organization/project" terpisah) — MVP diasumsikan 1 perusahaan/instance.
- Optimasi multi-supplier / negosiasi harga otomatis.
- Forecasting demand/sales produk jadi (fokus MVP hanya raw material & inventory) — kemungkinan modul lanjutan.
- Aplikasi mobile native (MVP berbasis web responsive).
- Notifikasi otomatis via WhatsApp/email (fase lanjutan).
- Async job processing (Celery/Redis) — MVP synchronous, ditambahkan hanya jika ada sinyal kebutuhan nyata (volume/waktu proses).

## 5. Functional Requirements

### FR-1 Data Ingestion
- FR-1.1 User dapat mengupload file CSV/Excel berisi data historis konsumsi material (kolom minimal: kode material, tanggal, jumlah pemakaian, satuan).
- FR-1.2 Sistem memvalidasi format file dan menampilkan error yang jelas jika format tidak sesuai (kolom hilang, tipe data salah, dsb) — sebelum data dipakai untuk forecast.
- FR-1.3 Sistem menampilkan preview data (beberapa baris pertama) sebelum diproses, agar user bisa mengecek hasil parsing.
- FR-1.4 Setiap upload disimpan sebagai `upload_session` dengan riwayat (siapa upload, kapan, jumlah baris, jumlah material terdeteksi).
- FR-1.5 File upload disimpan sementara (temp storage, TTL 1 jam) sampai divalidasi, lalu dipindah ke penyimpanan permanen jika valid.

### FR-2 Master Data Material
- FR-2.1 CRUD master data material: kode, nama, kategori, satuan, lead time supplier (hari), minimum order quantity (MOQ), safety stock manual (opsional override).
- FR-2.2 Import master data material via Excel/CSV.

### FR-3 Auto Model Selection Engine
- FR-3.1 Sistem mengklasifikasikan pola demand tiap material berdasarkan ADI (Average Demand Interval) dan CV² (Coefficient of Variation squared) ke salah satu kuadran: smooth, erratic, intermittent, lumpy.
- FR-3.2 Sistem menjalankan backtesting (rolling-origin) untuk setiap metode forecasting yang cocok dengan kuadran & ketersediaan data, menghitung MASE sebagai metrik utama.
- FR-3.3 Sistem melakukan guardrail check (bias & tracking signal) dan memberi penalti skor pada metode dengan bias sistematis besar.
- FR-3.4 Sistem menghitung skor akhir tertimbang (weighted scoring: MASE + guardrail + kecocokan kuadran) dan memilih metode dengan skor tertinggi.
- FR-3.5 Sistem menghasilkan penjelasan bahasa natural tentang metode yang dipilih dan alasannya.
- FR-3.6 Jika metode terpilih gagal saat eksekusi, sistem otomatis mencoba kandidat berikutnya (berdasarkan urutan skor), dan mencatat proses fallback ini secara transparan di penjelasan hasil.
- FR-3.7 User dapat melihat metode yang dipakai per item dan (opsional) memicu ulang forecast dengan metode berbeda secara manual.
- FR-3.8 Daftar metode aktif dan bobot scoring dapat dikonfigurasi tanpa mengubah kode (melalui konfigurasi/environment variable).
- FR-3.9 **Sebelum menjalankan forecast** (belum generate), user dapat memilih mode: **"Otomatis (Direkomendasikan)"** — sistem yang memilih metode via Auto Model Selection Engine — atau **memilih metode forecasting secara manual** dari daftar metode yang tersedia (ETS/ARIMA/LightGBM/Croston, dst) untuk run tersebut.
- FR-3.10 Jika user memilih metode manual, sistem **langsung memakai metode itu** (skip proses klasifikasi & scoring), tapi tetap menjalankan backtest untuk melaporkan MASE dan tetap menghasilkan penjelasan bahasa natural — supaya user tetap tahu seberapa akurat pilihannya secara historis.
- FR-3.11 Jika metode manual yang dipilih gagal dijalankan (mis. data tidak cukup untuk metode itu), sistem mengembalikan error yang jelas (`UNSUPPORTED_FORECAST_METHOD` atau `MODEL_SELECTION_FAILED`), bukan diam-diam pindah ke metode lain — karena user sudah memilih secara sadar.

### FR-4 Rekomendasi Reorder & Safety Stock
- FR-4.1 Sistem menghitung safety stock berdasarkan variabilitas demand, lead time, dan target service level (dapat dikonfigurasi, mis. 95%).
- FR-4.2 Sistem menghitung reorder point = (demand rata-rata selama lead time) + safety stock.
- FR-4.3 Sistem menghasilkan rekomendasi jumlah order (order quantity) mempertimbangkan MOQ.
- FR-4.4 Sistem menandai item dengan status "Perlu Reorder Segera", "Aman", atau "Overstock".

### FR-5 Planner Override & Audit Trail
- FR-5.1 Planner dapat override manual hasil forecast atau rekomendasi reorder untuk item tertentu.
- FR-5.2 Setiap override wajib menyertakan alasan (tidak boleh kosong — ditolak dengan error jika kosong).
- FR-5.3 Override disimpan sebagai revisi baru (append-only), tidak menghapus/menimpa hasil sistem asli.
- FR-5.4 Riwayat override (siapa, kapan, nilai sebelum/sesudah, alasan) dapat dilihat kembali oleh Admin/Manajer.

### FR-6 Dashboard & Visualisasi
- FR-6.1 Dashboard ringkasan: jumlah item perlu reorder, akurasi forecast rata-rata (MASE), tren konsumsi total.
- FR-6.2 Grafik tren aktual vs forecast per item material, termasuk confidence interval (lower/upper).
- FR-6.3 Tabel status stok seluruh item dengan filter/sort (kategori, status, urgensi).
- FR-6.4 Tampilan riwayat override per item.

### FR-7 Export & Laporan
- FR-7.1 Export hasil forecast & rekomendasi reorder ke Excel.
- FR-7.2 Export laporan ringkasan ke PDF.

### FR-8 User Management
- FR-8.1 Login dengan role: Admin, PPIC (Planner), Purchasing, Viewer.
- FR-8.2 Role menentukan akses (mis. Purchasing hanya bisa lihat rekomendasi reorder, tidak bisa override atau ubah master data).

## 6. Metode Forecasting yang Didukung

| Kategori | Metode | Kapan Dipakai | Status |
|---|---|---|---|
| Baseline/Klasik | ETS (Exponential Smoothing) | Data < 30 titik, trend sederhana, pola smooth | MVP |
| Klasik | ARIMA | Data stasioner tanpa musiman kuat | MVP |
| Modern | Prophet (Meta) | Ada musiman & missing values | MVP |
| Modern | LightGBM | Data besar (≥200 titik), pola kompleks | MVP |
| **Intermittent Demand** | **Croston's Method / SBA** | **Pola intermittent/lumpy (konsumsi sporadis — umum pada raw material)** | **MVP — ditambahkan hasil rekonsiliasi (lihat `RECONCILIATION.md`)** |
| Post-MVP | SARIMA, Holt-Winters, Theta, TBATS | Musiman kompleks | Post-MVP |
| Post-MVP | NeuralProphet, XGBoost | Alternatif engine modern | Post-MVP |
| Enterprise | LSTM, N-HiTS, TFT | Long-horizon, multivariate | Enterprise tier |

> ⚠️ **Penting:** empat metode "generik" (ETS/ARIMA/Prophet/LightGBM) tidak cocok untuk pola **intermittent** atau **lumpy** — pola yang justru paling umum pada konsumsi raw material (item yang jarang dipakai tapi kritikal). Karena itu Croston's Method/SBA wajib ada di MVP, bukan opsional, agar item-item tersebut tidak selalu berakhir `MODEL_SELECTION_FAILED`.

Sistem melakukan **klasifikasi pola demand** (ADI/CV²) lalu **backtesting otomatis** (MASE) untuk memilih metode dengan error terkecil dan tercocok dengan pola tiap item material — bukan satu metode yang dipaksakan untuk semua item.

## 7. Non-Functional Requirements

- **Usability**: Interface mudah digunakan oleh staff PPIC yang terbiasa dengan Excel; hasil forecast disertai penjelasan bahasa natural, bukan hanya angka statistik.
- **Performance**: Forecasting run untuk ratusan item material selesai dalam hitungan detik–menit; timeout per engine (default 45 detik) agar satu item bermasalah tidak memblokir seluruh run.
- **Reliability**: Validasi data ketat; kegagalan satu engine tidak boleh menggagalkan seluruh proses seleksi (exclude & lanjut ke kandidat lain).
- **Security**: Autentikasi JWT (Supabase Auth), role-based access control, file upload divalidasi (tipe, ukuran maksimum).
- **Scalability**: Registry/Factory pattern untuk model engine — metode baru bisa ditambah tanpa mengubah orchestrator/endpoint/test yang sudah ada.
- **Auditability**: Setiap upload, forecast run, dan override tercatat lengkap (siapa, kapan, versi data, alasan).
- **Data & Model Integrity**: Data historis asli tidak pernah dimodifikasi secara silent; hasil forecast/override tidak pernah di-overwrite, selalu sebagai entri baru.
- **Testability**: Seluruh logic inti (klasifikasi, scoring, reorder calculation) dikembangkan dengan TDD dan coverage minimum sesuai `AGENTS.md`.

## 8. Asumsi & Batasan

- Data historis minimal 12 periode (`BACKTEST_MIN_PERIODS`, default 12) agar backtesting bermakna; di bawah itu → error `INSUFFICIENT_DATA` sebelum backtest dijalankan (fail fast).
- Format file upload mengikuti template kolom wajib yang disediakan sistem.
- MVP tidak terhubung real-time ke ERP — proses berbasis upload manual berkala.
- MVP diasumsikan 1 perusahaan/instance (bukan multi-tenant SaaS) — lihat "Keputusan Terbuka" di `RECONCILIATION.md`.
- Forecasting dijalankan synchronous untuk MVP; async processing (Celery/Redis) hanya ditambahkan jika ada sinyal kebutuhan nyata.

## 9. Metrik Keberhasilan (Success Metrics)

- Pengurangan kejadian stockout raw material minimal 30% dalam 3 bulan penggunaan.
- Pengurangan waktu penyusunan rencana pengadaan dari manual Excel (berjam-jam) menjadi < 30 menit.
- Akurasi forecast (rata-rata MASE) berada di bawah ambang batas yang disepakati (disesuaikan setelah data riil tersedia).
- Tingkat kepercayaan planner terhadap sistem (diukur dari frekuensi override — target: override menurun seiring waktu karena planner makin percaya, bukan karena dipaksa).

## 10. Contoh User Stories

1. Sebagai **Planner PPIC**, saya ingin mengupload data pemakaian material bulan lalu (banyak SKU sekaligus) dalam satu file CSV, agar sistem otomatis memproses forecast tanpa saya hitung manual per item.
2. Sebagai **Planner PPIC**, saya ingin melihat preview & validasi data sebelum diproses, agar saya bisa memperbaiki data yang salah lebih dulu.
3. Sebagai **Planner PPIC**, saya ingin membaca penjelasan bahasa natural kenapa sistem memilih metode tertentu untuk suatu item, agar saya bisa menilai apakah masuk akal sebelum dipakai untuk keputusan pengadaan.
4. Sebagai **Planner PPIC**, saya ingin bisa override rekomendasi sistem untuk item tertentu (mis. karena ada informasi dari lapangan yang sistem tidak tahu), dengan mencatat alasannya.
5. Sebagai **Tim Purchasing**, saya ingin melihat daftar material yang perlu segera di-reorder beserta jumlah rekomendasinya, agar saya bisa langsung membuat PO.
6. Sebagai **Manajer**, saya ingin melihat dashboard akurasi forecast dan riwayat override, agar saya bisa menilai keandalan sistem dan pola judgment planner dari waktu ke waktu.
7. Sebagai **Admin**, saya ingin mengatur lead time dan MOQ per material, serta bobot scoring engine, agar perhitungan reorder point dan pemilihan model sesuai kondisi riil.
8. Sebagai **Planner PPIC**, saya ingin bisa memilih sendiri metode forecasting (mis. paksa pakai ARIMA) sebelum generate, karena saya sudah tahu dari pengalaman metode mana yang biasanya cocok untuk item tertentu — tanpa harus menunggu hasil auto-selection dulu baru override.

## 11. Roadmap Setelah MVP (Future Considerations)

- Integrasi langsung ke ERP/database perusahaan (real-time atau scheduled sync).
- Notifikasi otomatis (email/WhatsApp) saat item mencapai reorder point.
- Forecasting demand produk jadi, terhubung dengan modul raw material (backward calculation via BOM).
- Multi-lokasi/gudang, multi-tenant (organization/project) untuk dijual sebagai SaaS ke banyak perusahaan.
- Engine tambahan: SARIMA, Holt-Winters, TBATS, NeuralProphet, XGBoost, dan tier enterprise (LSTM/N-HiTS/TFT).
- Async job processing (Celery/Redis) bila volume data/waktu proses sudah menuntutnya.

---
*Dokumen ini adalah living document. Lihat `RECONCILIATION.md` untuk histori keputusan penggabungan spesifikasi.*
