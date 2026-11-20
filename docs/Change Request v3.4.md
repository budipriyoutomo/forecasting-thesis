# Change Request v3.4: Modul Variabel Eksternal (19 November 2026)

| | |
|---|---|
| **Tanggal** | 19 November 2026 |
| **Sumber** | `Simulasi Thesis 1.xlsx` sheet **Pengumpulan Data**, tabel *Variabel Peramalan* (kolom S–AV, baris 2–52) |
| **Modul terdampak** | Fase 11.2b: `external_variables`, `external_variable_values`, `external_variable_service.py`, `engines/_ml.py`, halaman `/external-variables` |
| **Status** | §4 selesai diimplementasi (20 Nov 2026, belum commit). §5 berisi usulan jawaban, **menunggu konfirmasi penulis thesis** |

---

## 1. Ringkasan

Secara konsep modul sudah cocok dengan Excel. Variabelnya dinamis (numerik/flag, global/per produk, toggle aktif) dan dipakai RF/XGBoost sebagai fitur. Tapi **kalau data Excel diimport apa adanya, sebagian besar variabel akan di-drop engine tanpa pemberitahuan ke planner.**

| # | Temuan | Dampak | Prio |
|---|---|---|---|
| 1 | Periode di Excel = **tanggal 24** (`2024-01-24`), import tidak menormalisasi tanggal | `usable_exog` reindex ke periode demand (tgl 1), semua nilai jadi NaN, **semua variabel di-drop** | 🔴 P0 |
| 2 | Variabel yang di-drop hanya tercatat di `hyperparameters.exog_dropped`, tidak tampil di UI | Planner mengira variabel dipakai padahal tidak. Klaim thesis "model memakai variabel X" tidak bisa dibuktikan | 🔴 P0 |
| 3 | Nilai horizon setelah Okt 2026 hampir kosong | Bila demand sampai Okt 2026, hanya 6 variabel yang lolos (lihat §3) | 🔴 P0 (bergantung data) |
| 4 | Sel non-numerik: `-`, `NA`, `40,33\t`, teks cuaca | Import gagal di baris pertama yang kotor (all-or-nothing) | 🟡 P1 |
| 5 | Variabel turunan demand (Permintaan AM, Sensitivitas Harga Ep) | **Data leakage** bila jadi fitur | 🟡 P1 (metodologi) |
| 6 | Kode cuaca nominal (1/2/3) diperlakukan sebagai angka | Urutan palsu (Peralihan > Kemarau > Hujan) | 🟡 P1 |
| 7 | Variabel jarang (TBI tahunan, Pendapatan 2x/tahun) | Pasti di-drop karena tidak lengkap. Tidak ditangani di CR ini (lihat §4.6) | 🟢 P2 |
| 8 | Tidak ada template import & tidak ada ringkasan kelengkapan per variabel | Planner menyiapkan file manual dari sheet lebar ke format panjang | 🟢 P2 |
| 9 | Nilai horizon skenario 24 bulan = nilai **realisasi** 2026 | Hasil forecast & evaluasi terlalu optimistis (*oracle exog*), karena nilai itu belum diketahui saat forecast dibuat | 🟡 P1 (metodologi) |

---

## 2. Pemetaan Variabel Excel → Master Variabel Eksternal

Usulan seed `--profile thesis`. Kolom **Fitur ML?** adalah rekomendasi, keputusan final di §5.

| Grup | Kolom Excel | `code` | Tipe | Scope* | Fitur ML? | Catatan |
|---|---|---|---|---|---|---|
| Harga | AN Harga Produk (efektif) | `harga_efektif` | numeric | global | ✅ | = promo bila ada, else normal. **Pakai ini saja**, bukan T/U/AN sekaligus |
| Harga | T Harga normal | `harga_normal` | numeric | global | ❌ | Kolinear dengan `harga_efektif` |
| Harga | U Harga Promo | — | — | — | ❌ | Sudah terwakili `harga_efektif` + `diskon_produk` |
| Harga | V Harga Kompetitor (Cimory) | `harga_kompetitor` | numeric | global | ✅ | |
| Cuaca | W Temperature (°C) | `suhu` | numeric | global | ✅ | BMKG |
| Cuaca | Y Kode Cuaca/Musim | `musim_hujan`, `musim_kemarau` | flag | global | ✅ | **One-hot**, Peralihan = keduanya 0 |
| Cuaca | AA Kode Curah Hujan | `curah_hujan` | numeric | global | ✅ | Ordinal 1–4, nilai 1,5/2,5/3,5 boleh |
| Event | AB Promosi | `promo` | flag | global* | ✅ | Prioritas "Sangat tinggi" (Z46) |
| Event | AC Product Promotion Days | `hari_promo` | numeric | global* | ⚠️ | Ada `NA` (Jun 2024, Okt 2026) |
| Event | AD Product Discount (%) | `diskon_produk` | numeric | global* | ✅ | Pecahan 0–1 |
| Event | AE Competitor Promotion Days | `hari_promo_kompetitor` | numeric | global | ✅ | |
| Event | AF Competitor Discount (%) | `diskon_kompetitor` | numeric | global | ✅ | |
| Event | AG Libur Sekolah | `hari_libur_sekolah` | numeric | global | ✅ | Jumlah hari |
| Event | AH PRJ | `hari_prj` | numeric | global | ⚠️ | Hanya Jun–Jul, korelasi tinggi dengan libur sekolah |
| Event | AI Idul Fitri | `idul_fitri` | flag | global | ✅ | Prioritas "Tinggi" |
| Event | AJ Natal | `natal` | flag | global | ⚠️ | Selalu Desember, kolinear dengan fitur `month` |
| Event | AK Tahun Baru | `tahun_baru` | flag | global | ⚠️ | Selalu Januari, kolinear dengan fitur `month` |
| Konsumen | AL Preferensi Merk (TBI) | `tbi` | numeric | global | ❌ | Hanya Jan 2025 & Jan 2026 |
| Konsumen | AM Permintaan | — | — | — | ⛔ | **Ini target (demand), bukan variabel.** Jangan diimport |
| Konsumen | AO–AQ Perubahan harga/permintaan, Ep | — | — | — | ⛔ | Diturunkan dari demand → leakage; `#DIV/0!` saat harga tetap (S52) |
| Konsumen | AR Ketertarikan Makanan Sehat | `gt_makanan_sehat` | numeric | global | ✅ | Google Trends 1–100 |
| Konsumen | AS Ketertarikan Yogurt | `gt_yogurt` | numeric | global | ✅ | Ada sel teks `"40,33\t"` |
| Konsumen | AT Ketertarikan Probiotik | `gt_probiotik` | numeric | global | ⚠️ | Korelasi dengan `gt_yogurt`, cek dulu |
| Ekonomi | AU Inflasi | `inflasi` | numeric | global | ✅ | BPS, bulanan |
| Ekonomi | AV Pendapatan Masyarakat | `pendapatan` | numeric | global | ❌ | Feb & Agu saja; forward-fill bila mau dipakai |

\* **Scope** perlu dikonfirmasi (§5 no. 2). Bila promo hanya berlaku untuk varian tertentu, `promo`, `hari_promo`, `diskon_produk`, dan `harga_efektif` harus `scope = product`.

Rekomendasi: aktifkan **8–10 variabel** saja. Data hanya 24–34 bulan, sedangkan kandidat fiturnya ±20 + lag + `month`. Risiko overfit RF/XGB tinggi.

---

## 3. Kelengkapan Data per Horizon

Engine hanya memakai variabel yang **lengkap untuk histori + seluruh horizon** (`usable_exog`). Kolom yang masih terisi untuk Nov–Des 2026 (baris 39–40):

| Terisi | Kosong |
|---|---|
| `hari_promo_kompetitor`, `diskon_kompetitor`, `hari_prj`, `idul_fitri`, `natal`, `tahun_baru` | Semua harga, suhu, musim, curah hujan, promo produk, libur sekolah, Google Trends, inflasi |

Dampak per skenario:
- **Demand thesis = 2024–2025 (24 periode, seed `--profile thesis`)**: horizon jatuh di 2026, dan baris Jan–Okt 2026 terisi. ✅ Aman untuk horizon ≤ 10 bulan.
- **Demand diperpanjang sampai Okt 2026** (kolom AM tersedia): horizon Nov–Des 2026 → hanya 6 variabel di atas yang lolos. Nilai ke depan wajib diisi dulu.

> ⚠️ **Oracle exog (temuan #9).** Pada skenario 24 bulan, nilai Jan–Okt 2026 di Excel adalah nilai **realisasi** (suhu, Google Trends, inflasi yang sudah terjadi). Bila dipakai apa adanya sebagai nilai horizon, model "melihat masa depan" untuk variabel yang tidak *known in advance*, sehingga akurasi terhadap aktual 2026 terlalu optimistis. Hal yang sama berlaku untuk backtest pada data uji. Pilihan:
> - (a) Isi horizon variabel non-*known in advance* dengan aturan di tabel bawah (rata-rata historis / naive), bukan nilai realisasi; **atau**
> - (b) Pakai nilai realisasi, tetapi tulis eksplisit sebagai batasan penelitian (skenario *perfect foresight*).
>
> Harga, promo, diskon, event, dan libur sekolah tidak terdampak karena memang diketahui di muka.

Sumber nilai horizon yang bisa dipertanggungjawabkan di thesis:

| Variabel | Sumber nilai ke depan |
|---|---|
| Harga, promo, diskon **produk sendiri** | Rencana marketing/kalender promo (known in advance) |
| Harga & promo/diskon **kompetitor** | Nilai periode terakhir (naive): tidak diketahui perusahaan di muka. **Sebutkan sebagai asumsi** |
| Event, libur sekolah | Kalender Kemenag & kalender pendidikan (known in advance) |
| Suhu, curah hujan, musim | Prakiraan musim BMKG, atau rata-rata bulan yang sama tahun sebelumnya |
| Google Trends, inflasi | Nilai periode terakhir (naive) atau target BI. **Sebutkan sebagai asumsi** |

---

## 4. Perubahan Kode

### 4.1 🔴 Normalisasi periode ke awal bulan

**Masalah:** `import_values` memakai `pd.to_datetime(...).date()` tanpa normalisasi. `2024-01-24` ≠ `2024-01-01`.

**Perubahan:**
- [x] Helper `normalize_period(value) -> date` di `app/services/forecasting/preprocessing.py`: `date.replace(day=1)`. Hanya bulanan: `demand_history.period` per definisi bulanan (ARCHITECTURE §4) dan tidak ada `period_basis` untuk demand, jadi varian mingguan tidak dibuat
- [x] Dipanggil di `ExternalVariableService.import_values` **dan** `data_ingestion_service.extract_demand_rows` (sumber tunggal, jangan dua aturan)
- [x] Duplikat setelah normalisasi (dua baris di bulan yang sama untuk variabel + produk yang sama). **Dedupe dilakukan di service sebelum `upsert_values`**: repository saat ini menghapus baris lama per periode lalu `add_all` semua baris, sehingga dua baris dengan periode sama dalam satu batch akan melanggar unique constraint. Jumlahnya dilaporkan di respons import (`normalized`, `overwritten`)
  - Tanggal **sama** (mis. dua baris `2024-01-24`) → baris terakhir menang
  - Tanggal **berbeda** di bulan yang sama (mis. `2026-01-24` & `2026-01-25`) → **error**, bukan ditimpa. Ditemukan di `variable peramalan.xlsx` (20 Nov 2026): sel berformat `d-mmm`, planner mengetik "Jan-24" (= Jan 2024) dan Excel menyimpannya sebagai 24-Jan-**2026**. Jan 2024/2025/2026 menjadi `2026-01-24/25/26`, dan normalisasi akan melebur 3 tahun jadi satu (24 dari 36 baris tertimpa diam-diam). Pesan error memberi petunjuk perbaikan. `Simulasi Thesis (2).xlsx` sheet *Pengumpulan Data* **tidak** terdampak (format `mmm-yy`, tahun benar)
  - Demand: duplikat bulan sama **tidak** di-dedupe (perilaku lama dipertahankan; `demand_history` tanpa unique constraint dan `to_period_series` menjumlahkan per periode)
- [x] Respons import (additive, kompatibel): `{imported, normalized, overwritten}`; pesan API & toast frontend menyebut jumlah periode yang digeser / baris ganda
- [x] **Data demand lama**: script `python -m app.scripts.normalize_demand_periods` (laporan saja) / `--apply` (geser ke tgl 1). Baris bentrok (dua baris satu upload & produk di bulan sama, atau bulan itu sudah punya baris tgl 1) **tidak disentuh** dan dilaporkan → upload ulang file yang benar. Histori tidak dihapus/digabung, hanya `period` yang digeser
  - DB lokal (20 Nov 2026): 294 baris `demand_history`, 0 bukan tgl 1 → aman. **VPS belum dicek**: jalankan script di container backend sebelum forecast pertama setelah deploy
- [x] **Upload demand tidak diam-diam**: `demand_period_warnings` menambah peringatan ke upload session (tampil di `UploadPanel`): jumlah baris yang digeser ke awal bulan + produk-bulan dengan lebih dari satu tanggal asli (dijumlahkan saat forecast; sering tanda "Jan-24" terbaca 24-Jan)

**Test (RED dulu):**
- [x] `test_normalize_period_ke_awal_bulan` / `test_normalize_period_tidak_valid_raise_value_error`
- [x] `test_import_values_tanggal_24_dinormalisasi_ke_awal_bulan`
- [x] `test_import_duplikat_bulan_sama_baris_terakhir_menang`
- [x] `test_exog_tanggal_24_tetap_terpakai_engine` (integrasi: import → `build_exog` → `usable_exog` tidak drop)
- [x] `test_extract_demand_rows_normalisasi_periode`
- [x] `test_import_pesan_menyebut_normalisasi_periode` (API) + `externalVariable.test.ts` (`importSummary`)

### 4.2 🔴 Variabel yang di-drop harus terlihat

**Perubahan:**
- [x] `EngineResult`/`candidates_evaluated` sudah menyimpan `exog_used` & `exog_dropped`. Tambahkan **alasan** per variabel: `missing_history` | `missing_horizon` | `constant` (nilai tidak bervariasi, tidak berguna untuk tree)
- [x] Alasan `constant` dinilai dari **histori** saja (seluruh histori = data fit model final), bukan histori + horizon. Variabel yang konstan di histori tetapi berubah di horizon tetap tidak berguna untuk model tree
- [x] `usable_exog(exog, history, horizon)` mengembalikan `dict[code, reason]`, bukan `list[str]`. Signature dipecah histori/horizon supaya alasan bisa dibedakan
- [x] **Backward compatibility**: `hyperparameters.exog_dropped` pada hasil forecast yang sudah tersimpan berformat `list[str]`. Frontend menerima kedua format (list lama → "Alasan tidak tercatat (forecast lama)"). Tidak ada migrasi data hasil forecast lama
- [x] Frontend hasil forecast: komponen `ExogUsage`, badge "Variabel eksternal dipakai n / m" + daftar yang di-drop beserta alasannya. **Daftar ditampilkan langsung, bukan tooltip**: bukti untuk thesis harus terbaca tanpa hover dan bisa di-screenshot. Hanya tampil untuk hasil yang sudah dipilih dan metode yang memakai exog (RF/XGBoost)
- [x] Halaman `/external-variables`: kolom **Kelengkapan** = `n_filled/n_expected (pct%)`, merah bila < 100%, `title` berisi periode yang belum terisi (maks. 6)
- [x] Endpoint baru `GET /external-variables/coverage?horizon=` (default 12, 1–120) → `[{variable_id, code, first_period, last_period, n_expected, n_filled, missing_periods[]}]`
  - Target periode = bulan pertama..terakhir `demand_history` (lintas produk) + `horizon` bulan
  - Variabel per produk dihitung terisi bila **ada** produk yang punya nilai di periode itu (indikasi kasar; keputusan per produk tetap di `usable_exog` saat forecast)
  - [x] Default form forecast (`forecast/new/config`) diturunkan dari 30 ke **12** dan label "Horizon (hari)" (sisa v2.0) diganti "Horizon (bulan)", supaya sama dengan horizon kolom Kelengkapan. 30 bulan ke depan hampir pasti membuat semua variabel di-drop (`missing_horizon`). `horizon_unit` di DB tetap `days` (kolom legacy, tidak dipakai engine)

**Test:**
- [x] `test_usable_exog_alasan_drop_horizon_vs_histori`
- [x] `test_usable_exog_drop_variabel_konstan`
- [x] `test_usable_exog_konstan_dinilai_dari_histori_saja`, `test_usable_exog_tanpa_exog`
- [x] `test_periods_by_variable` (repo), `test_period_range_*` (repo demand), `test_coverage_*` (service & API, termasuk 422 horizon 0)
- [x] `externalVariable.test.ts` (`exogUsage`: format lama `list` dan baru `dict`), `ExogUsage.test.tsx`, `ForecastResults.test.tsx`
- [x] `ExternalVariablesTable.test.tsx`: kolom kelengkapan

### 4.3 🟡 Import lebih toleran & bisa dari format lebar

**Perubahan:**
- [x] Parser angka bersama `parse_decimal_id(raw)` di `app/utils/tabular.py`:
  - trim whitespace/tab/nbsp, koma desimal (`40,33\t` → 40.33), titik ribuan bila ada koma (`1.234,5`)
  - `%` → pecahan (`10%` → 0.10)
  - prefix `Rp`/`IDR` → pemisah ribuan `,` maupun `.` dibuang (`Rp 9,900`, `Rp 8.200`, `Rp 3,040,000`). Ditemukan di file Excel: harga berupa **teks** `"Rp 9,900"` (format Inggris)
  - ≥ 2 grup ribuan berkoma tanpa prefix (`3,040,000`) → ribuan. **Satu grup tanpa prefix (`9,900`) tetap koma desimal (9.9)**: ambigu, jadi harga sebaiknya ditulis dengan `Rp` atau sebagai sel angka
  - kosong / `-` / `NA` / `#N/A` → **dilewati** (bukan error), dilaporkan per variabel di `skipped`
  - teks lain (mis. `Hujan`) → error
- [x] Mode **validasi dulu** (dry-run): `POST /external-variables/values/import?dry_run=true` → `{dry_run, valid, errors[≤100], n_errors, imported, normalized, overwritten, skipped, warnings, format}`, tanpa menulis. Import biasa tetap all-or-nothing; pesan error menyebut jumlah error lain
- [x] **Format lebar**: kolom `period` + satu kolom per kode variabel (+ `product_code` opsional). Deteksi otomatis: tanpa kolom `variable_code` → format lebar. Kolom tak dikenal → `warnings`. `product_code` hanya dipakai variabel per produk; variabel global mengabaikannya (di format panjang tetap error)
- [x] **"Unduh template"**: `GET /external-variables/template?horizon=12` → `.xlsx` sheet `nilai` (period × variabel aktif, **terisi nilai global yang sudah ada**) + sheet `petunjuk`. Kolom `product_code` hanya muncul bila ada variabel aktif per produk; baris per produk ditambahkan planner
- [x] Frontend: tombol *Unduh template*, *Validasi file* (hasil di `ImportValidationResult`: semua error, sel dilewati, peringatan), *Import nilai* (toast menyebut sel dilewati). Teks bantuan menjelaskan dua format

**Test:**
- [x] `test_parse_decimal_id` (koma, tab, `%`, `Rp`, ribuan), `test_parse_decimal_id_kosong_dilewati`, `test_parse_decimal_id_tidak_valid`
- [x] `test_import_format_lebar`, `test_import_xlsx_lebar_sel_kotor_excel_thesis`, `test_import_format_lebar_tanpa_kolom_period`, `test_import_long_sel_kosong_dilewati_dan_dilaporkan`
- [x] `test_import_dry_run_kumpulkan_semua_error`, `test_import_dry_run_valid_tidak_menulis`, `test_import_error_menyebut_jumlah_error_lain`, `test_import_tanggal_berbeda_di_bulan_sama_ditolak`
- [x] `test_template_xlsx_variabel_aktif_periode_demand_plus_horizon`, `test_template_diisi_lalu_diimport_ulang` (round trip)
- [x] API: dry-run & template; frontend: `ImportValidationResult.test.tsx`, `importSummary` (sel dilewati)
- [x] Uji manual data asli (20 Nov 2026): 6 kolom `Simulasi Thesis (2).xlsx` → format lebar → dry-run valid, 204 nilai, 0 error; `gt_yogurt` Apr 2024 = 40,33, `harga_efektif` Jun 2024 = 8.200 (cocok §4.7)

### 4.4 🟡 Kategori nominal (musim)

Tidak perlu tipe baru. Cukup dua variabel flag (`musim_hujan`, `musim_kemarau`) di seed thesis + catatan di form: *"Variabel kategori (lebih dari 2 nilai) buat sebagai beberapa flag."*

- [x] Validasi ringan saat import (dan dry-run): variabel `numeric` yang nilainya di file **tepat** bilangan bulat 1..k dengan 3 ≤ k ≤ 5 → `warnings`: *"Variabel 'x' hanya berisi bilangan bulat 1–k: apakah ini kode kategori? Pertimbangkan satu variabel flag per kategori."* (non-blocking). k = 2 tidak diperingatkan (sering jumlah/ordinal biasa)
- [x] Catatan di form variabel: kategori > 2 nilai dibuat sebagai beberapa flag
  - Catatan: `curah_hujan` (ordinal 1–4) juga akan kena peringatan ini bila datanya hanya bulat. Variabel dengan nilai pecahan (1,5 / 2,5 / 3,5) tidak kena. Peringatan tetap non-blocking, planner boleh mengabaikan untuk variabel ordinal

### 4.5 🟡 Cegah leakage

- [ ] ~~Kolom opsional `external_variables.is_derived_from_demand` (422 `EXOG_LEAKAGE_BLOCKED`)~~ — **tidak dipilih**
- [x] Cukup **tidak di-seed** (Permintaan AM, Perubahan harga/permintaan, Ep — lihat §4.7, `test_variabel_turunan_demand_tidak_di_seed`) + catatan di form variabel: *"Jangan buat variabel turunan demand … model akan mencontek target"*

### 4.6 ~~Forward-fill opsional untuk variabel jarang~~ (dikeluarkan dari CR ini)

Usulan awal: kolom `external_variables.fill_method` (`null` | `ffill`) untuk `tbi` & `pendapatan`. **Dibatalkan** karena tidak menyelesaikan masalah:
- `pendapatan` hanya terisi Feb & Agu, sehingga Jan 2024 (sebelum nilai pertama) tetap kosong
- Horizon sengaja tidak di-ffill, sehingga variabel tetap di-drop oleh `usable_exog`
- Kedua variabel sudah bertanda ❌ (bukan fitur ML) di §2

Bila nanti dibutuhkan, planner cukup mengisi nilai bulanan secara eksplisit di file import.

### 4.7 Seed thesis

Memakai **usulan jawaban §5** (20 Nov 2026, menunggu konfirmasi penulis): 8 variabel aktif, semua global, horizon 2026 dua skenario. Mengubah keputusan cukup dengan mengganti `is_active` / `horizon_rule` di `thesis_data.py`.

- [x] `app/scripts/thesis_data.py`: `THESIS_EXTERNAL_VARIABLES` (23 variabel: kode, nama, tipe, unit, `is_active`, `horizon_rule`, sumber kolom) + `_EXOG_RAW` (Jan 2024–Des 2026, dari `Simulasi Thesis (2).xlsx` lewat `parse_decimal_id`, dibulatkan 4 desimal)
  - **Aktif (16, keputusan penulis 20 Nov 2026)**: `harga_efektif`, `harga_kompetitor`, `diskon_kompetitor`, `suhu`, `idul_fitri`, `hari_libur_sekolah`, `gt_yogurt`, `inflasi` + `tbi`, `gt_makanan_sehat`, `gt_probiotik`, `perubahan_harga`, `pendapatan` + ⚠️ `permintaan` (AM), `perubahan_permintaan` (AP), `ep` (AQ) — leakage, deskripsi variabel memuat peringatan
  - **Nonaktif (cadangan, 12)**: `harga_normal`, `promo`, `hari_promo`, `diskon_produk`, `hari_promo_kompetitor`, `hari_prj`, `musim_hujan`, `musim_kemarau`, `curah_hujan`, `natal`, `tahun_baru`
  - Aturan `zero_fill` (TBI, pendapatan, Permintaan, Perubahan permintaan, Ep): nilai Excel bila ada, selain itu 0, 36 bulan, kedua skenario. `perubahan_harga` (`price_change`) dihitung dari `harga_efektif` skenario yang sama dengan rumus AO
  - Tidak di-seed: Harga Promo (U), Harga Produk (AN = `harga_efektif`)
  - Pembersihan: `harga_efektif` dihitung ulang dari T/U (promo bila > 0; Feb 2026 Harga Promo = 0 berarti tidak promo). AN Nov–Des 2026 = 0 (artefak rumus, T kosong) → kosong, bukan harga 0. Kode musim → one-hot. `NA`/`-`/`#DIV/0!` → kosong
- [x] `thesis_exog_series(code, scenario)`:
  - `asumsi` (default): 2026 Jan–Des diisi per `horizon_rule`. `known` = realisasi 2026, bila kosong bulan sama 2025 (mis. `harga_efektif` Nov–Des, `hari_libur_sekolah` Nov–Des). `seasonal_mean` = rata-rata bulan sama 2024 & 2025 (`suhu`, Google Trends, `curah_hujan`). `same_month` = bulan sama 2025 (flag musim). `last_value` = Des 2025 (`inflasi`, harga/diskon/hari promo **kompetitor**, karena tidak diketahui perusahaan di muka)
  - `realisasi`: nilai Excel apa adanya (*perfect foresight*, Jan–Okt 2026)
- [x] `seed_demo_data.py --profile thesis [--exog-scenario asumsi|realisasi]`: buat variabel yang belum ada (definisi & status aktif yang sudah ada tidak diubah), lalu **ganti penuh** nilai variabel thesis sesuai skenario. Ganti skenario cukup dengan menjalankan ulang
- [x] Test: sampel sel (`suhu` Jan 2024 = 27,2; `gt_yogurt` Apr 2024 = 40,33; `harga_efektif` Jun 2024 = 8.200; `harga_kompetitor` Jun 2024 = 6.900; `inflasi` Jun 2024 = −0,0008; one-hot musim), sel NA tidak jadi angka, Idul Fitri bergeser, aturan per skenario, histori sama di kedua skenario, **8 variabel aktif lolos `usable_exog` untuk 24 bulan + horizon 12 (skenario asumsi)**, seed + ganti skenario + idempoten + CLI
- [x] Smoke test SQL asli (DB lokal, di-rollback): 23 variabel, 761 nilai

---

## 5. Keputusan yang Dibutuhkan (penulis thesis)

> **Status (20 Nov 2026):** kolom *Usulan jawaban* disusun dari analisis data `Simulasi Thesis (2).xlsx` sheet *Pengumpulan Data* + demand per SKU di `thesis_data.py`. **Menunggu konfirmasi penulis thesis.** Seed (`--profile thesis`, §4.7) sudah memakai usulan ini; mengubahnya cukup lewat `is_active` / `horizon_rule` di `thesis_data.py`.

| # | Pertanyaan | Usulan jawaban | Dasar |
|---|---|---|---|
| 1 | Daftar variabel final yang dipakai sebagai fitur ML? | ✅ **Diputuskan penulis 20 Nov 2026: 16 variabel** = 8 di bawah + seluruh kategori *Perilaku Konsumen* & *Ekonomi* (`tbi`, `gt_makanan_sehat`, `gt_probiotik`, `perubahan_harga`, `pendapatan`, `permintaan`, `perubahan_permintaan`, `ep`); sel error/kosong = 0, hasil ditampilkan apa adanya. ⚠️ **Leakage diterima secara sadar**: `permintaan` (AM) = Σ planning bulan yang sama (korelasi 1,00 dengan Σ actual 7 SKU) dan belum ada saat meramal; AP & Ep turunannya. Dengan AM, importance `permintaan` 38–42% dan MAD turun (RF 88.904 → 66.658, XGB 111.473 → 83.230, rata-rata 7 SKU) — perbaikan ini **bukan** akurasi operasional dan wajib disebut di Bab IV/batasan. <br>Usulan awal: **8 variabel**: `harga_efektif`, `harga_kompetitor`, `diskon_kompetitor`, `suhu`, `idul_fitri`, `hari_libur_sekolah`, `gt_yogurt`, `inflasi`. Cadangan uji sensitivitas (nonaktif): `gt_probiotik`, `hari_prj`, `musim_hujan`/`musim_kemarau` | Satu wakil per grup, buang yang redundan: `promo`, `diskon_produk`, `hari_promo`, `harga_efektif` saling berkorelasi \|r\| = 0,94–1,00 (2024–2025), jadi pakai satu saja (`harga_efektif`, sejalan dengan analisis Ep; alternatif `promo`, jangan dipakai berdua). `natal`/`tahun_baru` selalu Des/Jan, sudah diwakili fitur `month`. `tbi` & `pendapatan` hanya 3 & 6 titik. `suhu` (16 nilai unik) lebih informatif dari kode musim (3). **Seleksi berbasis aturan, bukan korelasi dengan demand**: `gt_probiotik` korelasinya paling kuat (r = −0,51), tetapi memilih fitur dari korelasi 24 bulan penuh ikut melihat data uji (leakage seleksi fitur) |
| 2 | Harga & promo berlaku sama untuk semua varian (global) atau per SKU? | **Global** | Excel hanya punya satu kolom harga/promo untuk semua varian. Per SKU hanya bila penulis punya data promo per varian |
| 3 | Kolom AM "Permintaan" itu total semua SKU atau satu SKU? | **Total _planning_ 7 SKU, bukan actual.** Bukan fitur | 2024 cocok 12/12 bulan dengan Σ `planning`. 2025: 9 bulan selisih kelipatan 47.160 (s.d. 141.456), kemungkinan revisi plan / SKU tambahan, **perlu dicek penulis** |
| 4 | Analisis sensitivitas harga (Ep) masuk Bab IV sebagai analisis deskriptif? | **Ya, di luar model ML** | Catatan: Ep saat ini dihitung dari *planning*, seharusnya dari *actual*. Harga promo hanya berbeda di 5 bulan (2024–2025); bulan lain `#DIV/0!` → Ep sedikit titik, tulis sebagai keterbatasan |
| 5 | Periode demand thesis: 2024–2025 (24 bln) atau sampai Okt 2026 (34 bln)? | **24 bulan** | Demand *per SKU* 2026 tidak tersedia (AM 2026 hanya total planning). Desain terkuat: latih 2024–2025, forecast Jan–Okt 2026 (horizon 10), bandingkan dengan realisasi per SKU bila datanya bisa didapat |
| 6 | Nilai horizon cuaca: prakiraan BMKG atau rata-rata historis bulan yang sama? | **Rata-rata bulan yang sama 2024–2025** (`suhu`, Google Trends, `curah_hujan`) | Prakiraan BMKG yang dibuat akhir 2025 tidak tersedia lagi sekarang |
| 7 | Skenario 24 bln: horizon variabel non-*known in advance* diisi nilai realisasi 2026 atau aturan §3? | **Dua skenario.** Utama `asumsi`: known-in-advance (`harga_efektif`, `idul_fitri`, `hari_libur_sekolah`) = realisasi 2026; cuaca & Google Trends = rata-rata bulan sama; `inflasi` & **variabel kompetitor** = nilai Des 2025. Pembanding `realisasi` (*perfect foresight*) | Harga/diskon kompetitor **tidak** diketahui perusahaan di muka (koreksi atas §3 yang mengelompokkannya ke known-in-advance). Selisih akurasi dua skenario = nilai informasi variabel eksternal, bisa jadi temuan Bab IV |

---|---|---|
| 1 | Daftar variabel final yang dipakai sebagai fitur ML? | 10 variabel bertanda ✅ di §2 |
| 2 | Harga & promo berlaku sama untuk semua varian (global) atau per SKU? | Global |
| 3 | Kolom AM "Permintaan" itu total semua SKU atau satu SKU? | Total, hanya untuk analisis Ep, bukan fitur |
| 4 | Analisis sensitivitas harga (Ep) masuk Bab IV sebagai analisis deskriptif? | Ya, di luar model ML |
| 5 | Periode demand thesis: 2024–2025 (24 bln) atau sampai Okt 2026 (34 bln)? | 24 bln (sesuai seed sekarang). Bila 34 bln, LSTM jadi lebih layak & nilai horizon §3 wajib diisi |
| 6 | Nilai horizon cuaca: prakiraan BMKG atau rata-rata historis bulan yang sama? | Rata-rata historis, ditulis sebagai asumsi |
| 7 | Skenario 24 bln: horizon variabel non-*known in advance* (cuaca, Google Trends, inflasi) diisi nilai realisasi 2026 atau aturan §3? (lihat peringatan *oracle exog* di §3) | Aturan §3 (rata-rata historis / naive). Nilai realisasi hanya untuk skenario pembanding *perfect foresight* |

---

## 6. Dampak ke Dokumen Thesis

- **Bab III**: tabel variabel penelitian mengikuti §2 (kode, tipe, sumber data dari catatan S43–S51), plus aturan "variabel tidak lengkap untuk horizon dikeluarkan dari model".
- **Batasan penelitian**: nilai horizon variabel cuaca/ekonomi adalah asumsi (§3); TBI & pendapatan dikeluarkan karena frekuensi data rendah. Bila nilai realisasi 2026 dipakai sebagai horizon, sebutkan sebagai skenario *perfect foresight* yang akurasinya lebih optimistis daripada kondisi operasional.
- **Bab IV**: tampilkan feature importance hanya untuk variabel di `exog_used`. Analisis Ep terpisah dari model.

---

## 7. Urutan Kerja

| Urutan | Isi | Bergantung | Estimasi |
|---|---|---|---|
| 1 | §4.1 Normalisasi periode + dedupe + cek data demand lama | — | 0,5–1 hari |
| 2 | §4.2 Alasan drop + kolom kelengkapan + endpoint coverage (kompatibel format lama) | 1 | 1 hari |
| 3 | §4.3 Parser toleran, dry-run, format lebar, template | — | 1 hari |
| 4 | §4.7 Seed thesis (variabel bersih) | 1, 3, §5 no. 1–2, 7 | 0,5 hari |
| 5 | §4.4–4.5 | §5 | 0,25 hari |
| 6 | Update `docs/PRD.md` FR-12.3, `ARCHITECTURE.md` §4, `RECONCILIATION.md` bab v3.4 | 1–5 | 0,5 hari |

**Selesai jika:** data sheet *Pengumpulan Data* yang disalin ke **template import** (format lebar, header = `code` variabel, tanggal 24 dan koma desimal dibiarkan apa adanya) berhasil diimport tanpa edit nilai, dan hasil forecast KBYPL 200 menampilkan daftar variabel yang dipakai & di-drop beserta alasannya.

> Import langsung dari sheet asli **tidak** termasuk scope: header Excel berupa label (mis. "Temperature (°C)"), bukan `code`, dan tabelnya berada di kolom S–AV dengan baris catatan di S43–S51. Alternatif `import_alias` per variabel tidak diambil (infrastruktur prematur).