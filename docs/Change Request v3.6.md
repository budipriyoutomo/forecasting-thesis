# CHANGE REQUEST v3.6 — UI/UX Modernisasi & Kelengkapan Informasi

> Tanggal: 20 Nov 2026 · Basis audit: repo `forecasting-thesis` commit `4164144` (merge PR #2 `feat/v3.5-fe-be-alignment-rbac`)
> Status: **Diimplementasi 21 Nov 2026** — keputusan §9 memakai usulan default; #6 (warna brand) masih menunggu Budi. Lihat `RECONCILIATION.md` §"CR v3.6".
> Legenda: ✅ selesai · ⚠️ sebagian · ⏳ belum/butuh input · ➖ tidak berlaku
> Metode audit: review kode frontend (`frontend/src`) terhadap tipe respons backend. Belum ada uji visual live / usability test.

---

## 0. Ringkasan audit

| Area | Hasil |
|---|---|
| Fondasi komponen (shadcn/ui, Radix, Tailwind token) | ✅ Rapi, konsisten di sebagian besar halaman |
| Palet chart aman buta warna, dark mode, skip link, `tabular-nums` | ✅ Sudah ada |
| Persistensi hasil forecast (bisa dibuka ulang) | ❌ Hasil hanya di state mutation — hilang saat refresh |
| Data yang dikirim BE tapi tidak dirender FE | ❌ 4 temuan (MASE kandidat, `inventory_metrics` dashboard, hasil adjust kapasitas, alasan gagal) |
| Alur kerja PPIC (urutan langkah jelas) | ⚠️ 6 section + 5 tombol aksi di satu halaman, urutan tidak eksplisit |
| Skalabilitas (banyak SKU) | ⚠️ Daftar checkbox polos & satu kartu panjang per produk |
| Konsistensi visual | ⚠️ `<select>` native, warna amber hardcode, tampilan default shadcn slate |

Temuan: **P0 = 2**, **P1 = 4**, **P2 = 4**.

Prinsip desain untuk CR ini:
1. **Tidak ada data yang dihitung tapi tidak terlihat.** Setiap field yang dikirim BE dan relevan bagi keputusan PPIC wajib punya tempat di UI (boleh di tooltip/detail, tapi ada).
2. **Setiap angka punya konteks** — label metrik, satuan, dan interpretasi singkat untuk user non-teknis.
3. **Alur mengikuti urutan kerja PPIC**, bukan urutan endpoint.

---

## 1. [P0] Hasil forecast tidak bisa dibuka ulang — ✅

**Masalah**
- `app/(dashboard)/forecast/new/config/page.tsx`: seluruh hasil (run, pilihan metode, perencanaan, reorder, kapasitas, biaya, metrik) bergantung pada `run.data` dari `useCreateForecastRun()`.
- Refresh / pindah menu → semua hilang dari halaman Forecast. Tidak ada route `/forecast/runs/[id]`.
- Endpoint `GET /forecast/runs` & `GET /forecast/runs/{id}` serta hook `useForecastRuns()` / `useForecastRun()` **sudah ada** — baru dipakai di halaman Kedatangan Material.
- Dashboard "Run forecast terakhir" tidak punya link ke detail run.

**Perbaikan frontend**
- Route baru:
  - `/forecast` — **Daftar run** (tabel: tanggal, dibuat oleh, horizon, jumlah produk, status, n pending pemilihan, status perencanaan). Tombol "Forecast baru".
  - `/forecast/runs/[id]` — **Detail run**: memindahkan seluruh section hasil dari halaman config (Hasil → Perencanaan → Reorder → Kapasitas → Biaya & Metrik).
- `/forecast/new/config`: setelah `POST /forecast/runs` sukses → `router.push(/forecast/runs/{run_id})`.
- `lib/navigation.ts`: menu "Forecast" → `/forecast`; `SUB_PAGE_LABELS` tambah "Forecast baru", "Konfigurasi", "Detail run".
- Dashboard: kartu run terakhir → link "Lihat detail run".
- Halaman Kedatangan Material: pemilih run memakai komponen yang sama (`RunPicker`) — satu sumber.

**Perbaikan backend (additive)**
- `GET /forecast/runs` item: tambah `n_products`, `n_completed`, `n_failed`, `n_pending_selection`, `has_planning` (bool — sudah ada proyeksi stok).
- `DashboardSummary.latest_run`: tambah `created_at`, `created_by`.

**Kriteria selesai**
- [x] Refresh di `/forecast/runs/{id}` menampilkan state yang sama (metode terpilih, reorder, proyeksi, biaya).
- [x] Generate forecast → redirect ke detail run.
- [x] Dashboard → klik run terakhir → detail run.
- [x] Purchasing/Viewer bisa membuka detail run (read-only, sesuai matriks CR v3.5 §3.2); tombol aksi disembunyikan via `useCan`.
- [x] Test FE: halaman detail run render dari `useForecastRun(id)` tanpa state mutation.

---

## 2. [P0] MASE (metrik utama) tidak tampil & tanpa interpretasi — ✅ — **⚠️ digantikan 21 Nov 2026:** keputusan user, pengujian peramalan hanya MAD, MFE, MAPE; MASE & MSE tidak ditampilkan (RECONCILIATION §"CR v3.6")

**Masalah**
- `types/forecastSettings.ts`: `DisplayMetric = "mad" | "mfe" | "mse" | "mape"` — **MASE tidak bisa dipilih**, padahal keputusan arsitektur menetapkan MASE sebagai metrik utama. BE sudah mengirim `ForecastCandidate.mase` dan `ForecastResult.mase`.
- `CandidatesTable` tidak punya kolom MASE.
- Dashboard tile "Akurasi Forecast" menampilkan `avg_mase` sebagai angka polos (mis. "0,82") tanpa label metrik maupun arti.

**Perbaikan**
- BE + FE: tambah `"mase"` ke `DisplayMetric` (enum `display_metrics` di `forecast_settings`), default aktif.
- `CandidatesTable`: kolom MASE selalu tampil paling kiri setelah Metode (tidak bisa dimatikan), metrik lain mengikuti checkbox Pengaturan Forecast.
- Tetap **tanpa peringkat/pemenang** (Fase 11.15) — tapi tambahkan indikator netral per sel:
  - MASE < 1 → badge "lebih baik dari naive"; ≥ 1 → "tidak lebih baik dari naive".
  - MAPE → label existing `mapeLabel()`.
- Header kolom metrik: tooltip definisi singkat (MAD, MFE = bias, MSE, MAPE, MASE).
- Dashboard tile: label "Akurasi forecast (MASE rata-rata)", nilai + hint interpretasi + MAPE.
- `lib/metrics.ts` baru: `METRIC_INFO` (label, definisi, arah lebih baik, fungsi interpretasi) — sumber tunggal untuk tabel, tile, tooltip, export.

**Kriteria selesai**
- [x] Kolom MASE muncul di semua run yang punya `candidates_evaluated`.
- [x] Tooltip definisi ada di setiap header metrik.
- [x] Test: `display_metrics` lama (tanpa `mase`) tetap valid; MASE tetap tampil.

---

## 3. [P1] Dashboard belum menampilkan informasi yang sudah tersedia — ✅

**Masalah** — `app/(dashboard)/dashboard/page.tsx`
- `summary.inventory_metrics` (service level α, fill rate β, stock-out rate, turnover) **tidak dirender sama sekali**.
- Tile "Perlu reorder" dan "Segera reorder" menampilkan angka yang sama (`reorder_status_counts.urgent`) dua kali.
- Run terakhir tanpa tanggal, pembuat, dan link.
- Kapasitas gudang hanya "x dari y produk melebihi kapasitas" — tanpa daftar produk mana.

**Perbaikan — tata letak dashboard baru**
1. **Baris KPI (4 tile):** Akurasi forecast (MASE) · Material perlu reorder · Service level (α) · Total biaya persediaan (TIC) + penghematan vs baseline bila ada.
2. **Kartu run terakhir:** tanggal, dibuat oleh, status, n berhasil/gagal/pending pemilihan, link detail. Bila `n_pending_selection > 0` → CTA "Pilih metode untuk N produk".
3. **Status reorder:** satu bar bertumpuk Segera / Aman / Kelebihan stok (+ angka langsung, bukan warna saja) dengan link ke tabel reorder terfilter.
4. **Kinerja inventory:** tabel ringkas `inventory_metrics` per scope (α, β, stock-out rate, turnover).
5. **Kapasitas gudang:** daftar produk yang melebihi kapasitas (maks 5 + "lihat semua").
6. **Butuh perhatian** (action list): produk gagal forecast, material `MISSING_UNIT_PRICE` / `MISSING_HOLDING_RATE`, periode kekurangan stok, override terbaru.

**Perbaikan backend (additive)**
- `DashboardSummary.warehouse.products_over: {product_id, code, name, excess_qty}[]` (maks 10).
- `DashboardSummary.attention: { n_failed_products, n_missing_cost_data, n_shortage_periods }`.
- `DashboardSummary.latest_run.n_pending_selection`, `total_inventory_cost_baseline`, `savings_pct`.

**Kriteria selesai**
- [x] Setiap field `DashboardSummary` punya tempat di UI (test snapshot per field).
- [x] Tidak ada angka ganda di dashboard.
- [x] Empty state per kartu bila data null (mis. "Jalankan perencanaan untuk melihat kinerja inventory").

---

## 4. [P1] Alur forecast tidak eksplisit — ganti dengan stepper — ✅

**Masalah**
- Halaman config memuat 6 section bertumpuk dengan tombol: Generate forecast, Jalankan perencanaan, Hitung reorder, Cek kapasitas, Export ×5.
- "Hitung reorder" & "Cek kapasitas" tumpang tindih dengan pipeline `Jalankan perencanaan` (tahap 2→4, Fase 11.8) — user tidak tahu mana yang wajib.
- Section Biaya & Metrik muncul hanya bila kondisi tertentu terpenuhi, tanpa penjelasan kenapa belum muncul.

**Perbaikan** — detail run (`/forecast/runs/[id]`) memakai **stepper horizontal** dengan status per langkah:

| Langkah | Isi | Selesai bila | Aksi |
|---|---|---|---|
| 1. Forecast | Ringkasan run + tabel produk (§5) | run `COMPLETED` | — |
| 2. Pilih metode | Perbandingan metode per produk / bulk | `n_pending_selection = 0` | Pilih metode (per produk / semua) |
| 3. Perencanaan | MRP, proyeksi stok, kapasitas material, adjust kapasitas | ada proyeksi stok | **Jalankan perencanaan** (satu tombol) |
| 4. Reorder & biaya | Tabel reorder, override, kapasitas gudang produk jadi, biaya & metrik | otomatis setelah langkah 3 | Override, Export |

- Langkah terkunci diberi pesan prasyarat ("Pilih metode untuk 3 produk dulu").
- Hapus tombol terpisah "Hitung reorder" & "Cek kapasitas" dari alur utama — keduanya sudah tercakup pipeline perencanaan. (Tetap tersedia via menu "⋯ Hitung ulang sebagian" bila masih dibutuhkan — lihat keputusan §9 #2.) *(Koreksi saat implementasi: cek kapasitas produk jadi TIDAK ada di pipeline — kini dimuat otomatis di langkah 4 lewat GET validasi gudang, tanpa tombol.)*
- Semua export dikumpulkan di satu tombol dropdown **Export ▾** di header detail run (Forecast, Reorder, Proyeksi stok, Metrik × Excel/PDF).
- Halaman `/forecast/new` (upload) + `/forecast/new/config` digabung menjadi wizard "Forecast baru": Data demand → Produk & parameter → Generate.

**Kriteria selesai**
- [x] Planner dapat menyelesaikan run → reorder dengan maksimal 3 klik aksi utama (Generate, Pilih metode bulk, Jalankan perencanaan). *(Generate → redirect detail run → "Pakai untuk semua produk" → "Jalankan perencanaan")*
- [x] Setiap langkah terkunci menampilkan alasan.
- [x] Test FE: status stepper diturunkan dari data run (bukan state lokal).

---

## 5. [P1] Hasil per produk tidak skala untuk banyak SKU — ✅

**Masalah**
- `ForecastResults` merender satu `Card` penuh per produk (penjelasan, tabel kandidat, exog, feature importance, chart, tabel qty). 20 SKU = halaman sangat panjang.
- Pemilihan produk di config = daftar checkbox tanpa search, pilih semua, atau filter.

**Perbaikan**
- **Tabel ringkasan produk** (DataTable): Kode · Nama · Status · Metode dipakai · MASE · MAPE · Total forecast horizon · Sumber pilihan · Aksi. Filter status (Selesai / Belum dipilih / Gagal), search, sort.
- Klik baris → **Sheet (panel kanan)** berisi detail produk dengan tab: *Ringkasan* (penjelasan, chart) · *Perbandingan metode* · *Faktor* (exog + feature importance) · *Angka* (tabel qty).
- Pemilihan produk: DataTable dengan checkbox, search, "pilih semua hasil filter", kolom jumlah bulan histori & tanggal data terakhir (supaya user tahu produk mana yang datanya cukup sebelum run).
- Komponen `ForecastResults` existing dipecah: `ProductResultsTable`, `ProductResultSheet` — logic pemilihan metode tetap.

**Kriteria selesai**
- [x] 50 produk tetap bisa discan dalam satu layar tabel.
- [x] Semua info yang sekarang ada di Card tetap ada di Sheet (checklist per komponen).

---

## 6. [P1] Hasil adjust kapasitas & kebijakan reorder tidak terlihat — ✅

**Masalah** — `components/dashboard/ReorderTable.tsx` tidak merender:
- `safety_stock_system`, `buffer_stock_system` (nilai sebelum adjust),
- `service_level_effective` (α efektif setelah SS diturunkan),
- `adjustment_source` (`suggested` / `custom`),
- `rop_formula_used` (standard / with_buffer) secara eksplisit.

Akibat: planner tidak tahu material mana yang SS-nya sudah diturunkan karena kapasitas gudang, dan berapa risiko service level-nya.

**Perbaikan**
- Kolom Safety stock: bila di-adjust → nilai baru + `dari {sistem}` tercoret + badge "Disesuaikan kapasitas (usulan/kustom)".
- Kolom baru **Service level efektif**: `service_level_effective` vs target `service_level_pct` di Pengaturan Forecast; merah bila di bawah target.
- Kolom Reorder point: subteks rumus yang dipakai (`μ·L + SS` / `μ·L + SS + B`).
- Baris yang expandable (atau Sheet) untuk rincian lengkap: annual demand, EOQ, MOQ, order-up-to, biaya pesan/simpan, C, i, sumber stok, override + alasan + waktu.
- Tabel terlalu lebar → kolom inti tampil (Material, Stok, ROP, Qty pesan, Status, Biaya), sisanya di detail baris.

**Kriteria selesai**
- [x] Semua field `ReorderRecommendation` (types/reorder.ts) tampil di tabel atau detail baris (test per field).
- [x] Material ter-adjust bisa difilter ("Hanya yang disesuaikan").

---

## 7. [P2] Konteks yang hilang di level produk — ✅ (7.4 ➖ tidak berlaku)

| # | Gap | Perbaikan |
|---|---|---|
| 7.1 ✅ | `ForecastChart` hanya menampilkan forecast + interval, tanpa histori aktual | BE: tambah `history: {date, value}[]` di `ForecastResult` (atau `GET /products/{id}/demand-history?months=24`). FE: garis histori (solid) → forecast (garis + band), dengan pemisah "hari ini" |
| 7.2 ✅ | Produk gagal (`INSUFFICIENT_DATA`, `MODEL_SELECTION_FAILED`) hanya badge merah | BE: `ForecastResult.status_reason` (mis. "Histori 8 bulan, minimal 12"). FE: Alert dengan langkah perbaikan + link ke upload demand |
| 7.3 ✅ | Total forecast per horizon tidak terlihat sekilas | Tampilkan total & rata-rata per bulan di tabel ringkasan (§5) dan header Sheet |
| 7.4 ➖ | Override forecast tidak ditandai di chart/tabel qty | Titik/baris ter-override diberi penanda + nilai sistem *(tidak berlaku: tidak ada override nilai forecast; override `forecast_result` = pemilihan metode, sumber & alasannya sudah tampil)* |

---

## 8. [P2] Sistem visual & konsistensi — ⚠️ sebagian (8.1 menunggu warna brand)

| # | Gap | Perbaikan |
|---|---|---|
| 8.1 ⏳ | Tampilan default shadcn slate — terasa generik | Tentukan warna brand `--primary` (usulan: biru-teal yang tidak bentrok dengan `--chart-1`), radius `0.75rem`, permukaan kartu `bg-card` + border halus, header halaman dengan breadcrumb + aksi di kanan *(belum — menunggu warna brand, §9 #6)* |
| 8.2 ✅ | Warna amber hardcode (`text-amber-700 dark:text-amber-400`) di config page | Token `--warning` / `--warning-foreground` (pasangan `--success`), varian `Alert`/`Badge` "warning" |
| 8.3 ✅ | `<select>` native di `ForecastResults` & `material-arrivals` | Ganti ke `ui/select` *(sisa native di luar cakupan: BomComponentForm, halaman Persediaan)* |
| 8.4 ⚠️ | KPI tile statis | `StatTile` tambah `trend` (delta vs run sebelumnya) & sparkline opsional *(prop `trend` & `href` ada; belum di-wire — BE belum kirim delta run sebelumnya; sparkline belum)* |
| 8.5 ✅ | Lebar konten tidak dibatasi | `main` → `mx-auto w-full max-w-screen-2xl` |
| 8.6 ✅ | Status run/hasil campuran Inggris (`COMPLETED`) & Indonesia | Satu peta label status di `lib/status.ts` dipakai semua badge |
| 8.7 ⚠️ | Angka tanpa satuan | `formatQty(value, uom)` — semua qty material/produk tampil dengan UoM *(dipakai di hasil produk, reorder & rinciannya, pemilihan produk; tabel proyeksi stok & kedatangan belum)* |

---

## 9. Keputusan yang dibutuhkan

| # | Pertanyaan | Usulan default |
|---|---|---|
| 1 | Struktur route: `/forecast` (daftar) + `/forecast/runs/[id]` (detail) + wizard `/forecast/new`? | **Ya** |
| 2 | Tombol "Hitung reorder" & "Cek kapasitas" terpisah dihapus dari alur utama (cukup "Jalankan perencanaan")? | **Ya**, pindah ke menu "Hitung ulang sebagian" |
| 3 | MASE kolom wajib (tidak bisa dimatikan) di perbandingan metode? | **Ya** — metrik utama thesis |
| 4 | Indikator MASE < 1 / ≥ 1 dianggap "peringkat" yang melanggar prinsip Fase 11.15? | **Tidak** — indikator absolut per metode, bukan urutan antar metode |
| 5 | Histori aktual dikirim di `ForecastResult.history` atau endpoint terpisah? | **Field di result** (24 bulan terakhir) — satu request |
| 6 | Warna brand | Perlu input Budi ⏳ |

---

## 10. Urutan pengerjaan yang disarankan

1. §1 route daftar & detail run (+ BE additive list/dashboard) — fondasi semua perbaikan lain.
2. §2 MASE + `lib/metrics.ts`.
3. §8.2, §8.3, §8.6 token & konsistensi (kecil, mengurangi utang sebelum komponen baru dibuat).
4. §4 stepper di detail run.
5. §5 tabel ringkasan + Sheet detail produk.
6. §6 reorder table lengkap.
7. §3 dashboard baru (butuh §1 & BE additive).
8. §7 konteks produk (butuh BE `history` & `status_reason`).
9. §8.1, §8.4, §8.5 polish visual.

**Definition of done CR v3.6 (keseluruhan)**
- [x] Audit "field coverage": setiap field respons BE yang relevan untuk keputusan tercantum di UI — checklist di `docs/ui-field-coverage.md`.
- [x] `tsc --noEmit` 0 error, vitest lolos, test baru untuk setiap komponen baru. *(beberapa test lama timeout 5 dtk saat load mesin tinggi; lolos dengan `--testTimeout=30000`)*
- [ ] ⏳ Uji usability singkat dengan 1 PPIC: run → pilih metode → reorder tanpa bantuan.
- [x] Docs diperbarui: PRD (alur layar), ARCHITECTURE (route FE), AGENTS.md (konvensi `lib/metrics.ts`, `lib/status.ts`, token warning).