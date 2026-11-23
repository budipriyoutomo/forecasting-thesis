# CHANGE REQUEST v3.7 — Tampilan Hasil Forecast Run Per Metode (Format Thesis "Part 1 = Forecast")

> Tanggal: 23 Nov 2026 · Basis: repo `forecasting-thesis` commit `c60671c` ("update layout ui")
> Sumber requirement: sketsa tangan Budi "Part 1 = Forecast" (lampiran chat 23 Nov 2026)
> Status: ✅ Diimplementasi 23 Nov 2026 (dengan koreksi D8/D9 — lihat `RECONCILIATION.md` §"Tampilan Hasil Run Per Metode (Format Thesis) — CR v3.7")
> Legenda prioritas: **P0** wajib · **P1** sebaiknya · **P2** opsional

---

## 0. Ringkasan

Setelah forecast run selesai, langkah 1 "Forecast" di `/forecast/runs/[id]` saat ini menampilkan **tabel per produk**
(`ProductResultsTable`) — satu baris = satu produk, metode yang dipakai + MAD/MFE/MAPE, detail di Sheet. Perbandingan
antar metode hanya terlihat **per produk** (tab "Perbandingan metode" di Sheet).

Yang diharapkan (sketsa): tampilan **per metode**, persis struktur Bab 4 thesis, supaya hasil bisa langsung
dibaca/disalin ke dokumen thesis:

```
1. Metode Random Forest
   a. Hasil ramalan (forecasting)          b. Pengujian peramalan
   Varian | Jan-26 | Feb-26 | … | Des-26    Varian | MAD | MAPE | MFE
   PL     |        |        |   |          PL     |     |      |
   SB … SR                                 SB … SR
                                           Average |     |      |
2. Metode LSTM            (struktur sama)
3. Metode XGBoost         (struktur sama)
4. Metode Rata-rata bergerak (Moving Average)
5. Metode Exponential Smoothing
6. Analisis pemilihan metode terbaik + penjelasannya
```

**Kabar baik:** seluruh data mentahnya **sudah ada** di respons `GET /forecast/runs/{id}` — tiap
`ForecastResult.candidates_evaluated[]` menyimpan `method`, `mad`, `mfe`, `mape`, `forecast[]` (deret per periode),
dan `rank*` sejak 23 Nov 2026. Yang belum ada hanya **agregasi level run** (baris Average + metode terbaik
keseluruhan + alasannya), dan itu harus dihitung **backend** (aturan: peringkat dihitung backend, FE hanya
menampilkan — `lib/metrics.ts`, `selection.py`).

---

## 1. Gap analysis (kode saat ini vs sketsa)

| # | Kebutuhan sketsa | Kondisi kode `c60671c` | Gap |
|---|---|---|---|
| 1 | Tabel hasil ramalan **per metode**, baris = varian, kolom = bulan | Deret per metode ada di `candidates_evaluated[].forecast`, tapi hanya dirender per produk (`ForecastQtyTable`, vertikal, satu produk) | ❌ Komponen matriks varian × periode belum ada |
| 2 | Tabel pengujian per metode: varian × MAD, MAPE, MFE | Metrik per kandidat ada; `CandidatesTable` = metode × metrik untuk 1 produk (transpos dari yang diminta) | ❌ Komponen varian × metrik per metode belum ada |
| 3 | Baris **Average** per metode | Tidak dihitung di mana pun | ❌ Perlu agregasi backend |
| 4 | Urutan metode RF → LSTM → XGBoost → MA → ES | Kandidat diurutkan per **rank** per produk (berbeda tiap produk) | ❌ Perlu urutan baku "format thesis" |
| 5 | Kolom urutan **MAD, MAPE, MFE** | `ALL_METRICS` = MAD, MFE, MAPE | ⚠️ View ini pakai urutan sketsa (= urutan prioritas seleksi) |
| 6 | §6 Analisis metode terbaik **level run** + penjelasan | `selection_analysis` hanya **per produk**; tak ada kesimpulan "metode terbaik untuk seluruh varian" | ❌ Perlu `select_best_method` atas rata-rata metrik per metode |
| 7 | Varian = PL, SB, BB, LY, BF, MG, SR | = `product.code` | ✅ Tinggal mapping |
| 8 | Kolom periode Jan-26 … Des-26 | `ForecastPoint.date` | ✅ Tinggal format label |

---

## 2. Keputusan desain (default — bisa dikoreksi Budi)

| # | Keputusan | Alasan |
|---|---|---|
| D1 | Tampilan baru ditempatkan di **langkah 1 "Forecast"** sebagai view default **"Per metode (format thesis)"**; view lama **"Per produk"** tetap ada via toggle (`Tabs`/segmented control). Langkah 2–5 **tidak berubah**. | Planner tetap butuh view per produk untuk override metode; thesis butuh view per metode. Tidak membuang fitur yang sudah jalan. |
| D2 | Satu metode = satu section bernomor (1..N) **bertumpuk vertikal**, plus **navigasi lompat** (chip/anchor per metode) di atas. Bukan tab per metode. | Sketsa = dokumen berurutan; bertumpuk memudahkan scroll-and-compare & salin ke Word. |
| D3 | Urutan metode = konstanta `THESIS_METHOD_ORDER = ["random_forest","lstm","xgboost","moving_average","exponential_smoothing"]`; metode lain yang aktif ditambahkan di belakang (urut abjad). Metode **tidak aktif / tidak punya kandidat sama sekali** di run ini → section tidak dirender. | Mengikuti sketsa & Bab 3 thesis; tetap aman bila metode legacy diaktifkan. |
| D4 | Label varian = `product.code` (fallback `product_id` 8 char). Urutan baris = urutan produk di run (sama dengan `results[]`). | Sesuai sketsa. |
| D5 | Label periode `MMM-yy` locale **id-ID** → `Jan-26, Feb-26, Mar-26, … Des-26`. | UI berbahasa Indonesia. (Sketsa memakai "Dec" — ganti ke `en-US` bila thesis pakai Inggris.) |
| D6 | Angka hasil ramalan = **bilangan bulat** (`formatNumber` tanpa desimal, `tabular-nums`, rata kanan). Metrik: MAD/MFE 2 desimal, MAPE 2 desimal + `%`. MFE **bertanda**. | Qty produk diskrit; konsisten dengan `formatMetric`. |
| D7 | **Average** = rata-rata aritmetika per kolom atas varian yang metodenya berhasil (MFE rata-rata **bertanda**, sesuai rumus thesis). Bila ada varian yang gagal untuk metode itu, baris Average diberi catatan `n = x dari y varian`. | Sesuai sketsa; jujur soal coverage. |
| D8 | **Metode terbaik level run** = `select_best_method()` (fungsi yang sama dengan seleksi per produk, prioritas **MAD → MAPE → \|MFE\|**) diterapkan pada **rata-rata** per metode. Bila coverage antar metode berbeda (mis. LSTM gagal di 2 varian), peringkat dihitung atas **irisan varian yang berhasil di semua metode** (`ranking_basis = "common"`) dan UI menampilkan peringatan. | Satu aturan seleksi, tidak ada dua sumber kebenaran. Membandingkan rata-rata atas himpunan varian berbeda tidak adil. |
| D9 | §6 juga menampilkan **jumlah varian yang dimenangkan** tiap metode (dari `selection_analysis.best_method` per produk = pilihan **sistem**, bukan override planner) + tabel ringkas varian → metode terbaik. | Kesimpulan thesis bisa "RF terbaik secara rata-rata, tapi ES menang di 3 dari 7 varian" — itu temuan yang berharga. |
| D10 | Baris/sel **metode terbaik** per varian di tabel pengujian diberi penanda halus (ikon ✓ / bold), dan section metode terbaik run diberi badge "Terbaik". | Membantu membaca tanpa menambah tabel. |

> ⚠️ **Catatan metodologis (pushback):** rata-rata MAD lintas varian mencampur satuan/skala volume yang berbeda —
> varian bervolume besar mendominasi. Itu sah selama dinyatakan di thesis, tapi MAPE (skala-bebas) adalah pembanding
> lintas varian yang lebih adil. Aturan prioritas tetap MAD → MAPE → MFE (keputusan 23 Nov 2026); UI §6 menampilkan
> kalimat catatan ini agar pembaca tidak salah tafsir. Bila Budi ingin peringkat level run memakai MAPE dulu, cukup
> ubah parameter `criteria` di service — tidak perlu ubah UI.

---

## 3. Spesifikasi Backend (P0)

### 3.1 Endpoint baru

```
GET /api/v1/forecast/runs/{run_id}/method-comparison
Auth: get_current_user (semua role boleh baca — CR v3.5 §3.2)
```

Respons (envelope standar AGENTS.md §4):

```jsonc
{
  "success": true,
  "data": {
    "run_id": "…",
    "periods": ["2026-01-01", "2026-02-01", "…"],          // gabungan tanggal forecast, terurut
    "criteria": ["mad", "mape", "mfe"],                     // snapshot prioritas
    "methods": [                                            // urutan THESIS_METHOD_ORDER
      {
        "method": "random_forest",
        "label": "Random Forest",
        "rows": [
          {
            "product_id": "…",
            "status": "OK",                                 // "OK" | "FAILED" (metode gagal/dikecualikan untuk produk ini) | "NO_SERIES" (run lama tanpa deret)
            "forecast": { "2026-01-01": 1234.0, "…": 0 },   // periode → qty; {} bila tidak ada deret
            "mad": 12.3, "mape": 8.1, "mfe": -1.2,          // null bila FAILED
            "is_product_best": true                         // = selection_analysis.best_method produk ini
          }
        ],
        "average": { "mad": 10.1, "mape": 9.4, "mfe": -0.4, "n": 7, "n_total": 7 },
        "n_products_won": 4
      }
    ],
    "run_selection": {                                      // null bila < 1 metode dengan metrik
      "best_method": "random_forest",
      "ranking_basis": "all",                               // "all" | "common"
      "n_common": 7,
      "ranking": [ { "method": "random_forest", "rank": 1, "rank_mad": 1, "rank_mape": 2, "rank_mfe": 1, "mad": 10.1, "mape": 9.4, "mfe": -0.4 } ],
      "decided_by": "mad",
      "summary": "…",                                       // teks dari selection._explain
      "reasons": ["…"]
    },
    "product_winners": [ { "product_id": "…", "best_method": "random_forest", "decided_by": "mad", "method_used": "random_forest" } ]
  }
}
```

### 3.2 Implementasi

- **Fungsi murni baru** `backend/app/services/forecasting/method_comparison.py`:
  `build_method_comparison(results: list, criteria: Sequence[str]) -> dict`
  - Input: hasil `ForecastResult` run (yang sudah dimuat `ForecastSelectionService.list_results`).
  - Hanya hasil `status == "COMPLETED"` yang ikut; hasil gagal tetap muncul sebagai baris `FAILED` di setiap metode.
  - Kandidat yang tidak ada untuk suatu produk (metode gagal saat backtest → dikecualikan di `forecast_service`) → `status: "FAILED"`.
  - Kandidat tanpa `forecast` (run sebelum Fase 11.15) → `status: "NO_SERIES"`, metrik tetap diisi.
  - Mode **manual** → hanya satu metode yang punya baris; `run_selection` tetap dihitung (1 kandidat → `decided_by: null`).
  - Nilai NaN/inf → `null` (pakai `selection._finite`).
  - Average & `run_selection` sesuai D7/D8; panggil `selection.select_best_method(candidates=[{method, mad, mape, mfe}…], metrics=criteria)` — **jangan** menulis ulang logika peringkat.
  - Konstanta `THESIS_METHOD_ORDER` di modul ini.
- **Service**: tambah method `get_method_comparison(user_id, run_id)` di `ForecastSelectionService` (atau `ForecastRunService`) — validasi run ada (`_require_run`), ambil `criteria` dari snapshot pengaturan run bila ada, fallback `selection.DEFAULT_CRITERIA`.
- **Router**: `backend/app/api/v1/forecast.py` + schema Pydantic v2 di `backend/app/schemas/forecast.py` (`MethodComparisonOut` dll.). Daftarkan di OpenAPI.
- **Tidak ada perubahan DB / migrasi.** Read-only, dihitung on-the-fly (≤ 50 produk × 5 metode × 24 periode — murah).

### 3.3 Test (TDD — tulis dulu, Red → Green)

`backend/tests/unit/test_method_comparison.py`:
1. Matriks: 2 produk × 2 metode → baris & deret per periode benar, urutan metode mengikuti `THESIS_METHOD_ORDER`.
2. Average: MAD/MAPE rata-rata biasa; MFE rata-rata **bertanda** (−2 dan +2 → 0).
3. Metode gagal di 1 produk → baris `FAILED`, `average.n = n_total − 1`, `run_selection.ranking_basis == "common"`.
4. Peringkat level run sama dengan `select_best_method` atas rata-rata (MAD menang; MAD seri → MAPE; seri → |MFE|).
5. `n_products_won` & `is_product_best` dari `selection_analysis.best_method`, **bukan** `method_used` (override planner tidak mengubah hitungan).
6. Run lama tanpa deret → `NO_SERIES`; mode manual → 1 metode; NaN/inf → `null`.
7. Hasil produk gagal (`INSUFFICIENT_DATA`) muncul sebagai `FAILED` di semua metode dan tidak ikut rata-rata.

`backend/tests/integration/…` (pola endpoint yang sudah ada): 200 + envelope, 404 run tidak ada, 401 tanpa token.

---

## 4. Spesifikasi Frontend (P0)

### 4.1 Data layer
- `types/forecast.ts`: tipe `MethodComparison`, `MethodComparisonMethod`, `MethodComparisonRow`, `RunSelection` (cocok §3.1).
- `lib/api` → `api.forecast.getMethodComparison(runId, token)`.
- `hooks/useForecast.ts` → `useMethodComparison(runId)` (queryKey `["forecast-run", runId, "method-comparison"]`). **Invalidate** key ini di `onSuccess` `useSelectForecastMethod` / `useSelectForecastMethodForRun` (badge "dipakai" bisa berubah).
- `lib/format.ts` → `formatPeriodLabel(date: string): string` (`"2026-01-01"` → `"Jan-26"`, locale D5) + unit test.

### 4.2 Komponen baru (`components/forecast/method-view/`)

| Komponen | Isi |
|---|---|
| `MethodComparisonView` | Kontainer: navigasi lompat (chip per metode + "Analisis"), lalu `MethodSection` × N, lalu `BestMethodAnalysis`. State loading → `TableSkeleton`; error → `EmptyState`. |
| `MethodSection` | Judul `"{n}. Metode {label}"` + badge "Terbaik" bila `run_selection.best_method`. Berisi (a) `MethodForecastMatrix`, (b) `MethodMetricsTable`. Di layar ≥ `xl`, (a) dan (b) boleh berdampingan seperti sketsa? **Tidak** — (a) terlalu lebar (12+ kolom); tumpuk (a) di atas (b). |
| `MethodForecastMatrix` | `Table` shadcn: header "Varian" + satu kolom per `periods` (label D5) + kolom **Total**. Kolom Varian `sticky left-0 bg-background`; wrapper `overflow-x-auto`. Sel `FAILED` → "—" dengan tooltip "Metode gagal untuk varian ini"; `NO_SERIES` → "—" tooltip "Run lama: deret per metode tidak disimpan". |
| `MethodMetricsTable` | Header: Varian · MAD · MAPE · MFE (urutan sketsa, pakai `MetricHeader` untuk tooltip definisi). Nilai pakai `MetricValue`. Baris `is_product_best` → ikon ✓ kecil + `aria-label`. Footer **Average** (`TableFooter`, bold) + catatan `n = x dari y` bila `n < n_total`. |
| `BestMethodAnalysis` | §6: (1) tabel peringkat level run (Metode · Avg MAD · Avg MAPE · Avg MFE · Peringkat · Varian dimenangkan), baris #1 di-highlight; (2) kotak kesimpulan gaya `SelectionAnalysis` (summary + reasons + "Urutan prioritas … · penentu …"); (3) peringatan `ranking_basis === "common"`; (4) tabel ringkas Varian → Metode terbaik (sistem) → Metode dipakai (bila beda: "diganti planner"); (5) catatan metodologis D-pushback (1 kalimat, `text-muted-foreground`). |
| `CopyTableButton` (P1) | Tombol kecil "Salin" di tiap tabel → salin TSV ke clipboard (paste rapi ke Word/Excel). Toast sukses. |

Gunakan `METRIC_INFO`, `MetricHeader`, `MetricValue`, `methodLabel`, `formatNumber` yang sudah ada — **jangan** duplikasi.
Jangan hitung peringkat/rata-rata di FE; semua angka dari endpoint.

### 4.3 Integrasi di `RunDetail.tsx` (langkah 1)
- Ganti `{resultsView(false)}` di langkah `forecast` menjadi:
  ```
  <Tabs defaultValue="method">
    <TabsList><TabsTrigger value="method">Per metode (format thesis)</TabsTrigger>
              <TabsTrigger value="product">Per produk</TabsTrigger></TabsList>
    <TabsContent value="method"><MethodComparisonView runId={runId} products={products} /></TabsContent>
    <TabsContent value="product">{resultsView(false)}</TabsContent>
  </Tabs>
  ```
- Simpan pilihan tab di query string `?view=method|product` (agar refresh/tautan konsisten, sejalan prinsip CR v3.6 §1).
- Update `description` StepSection: "Hasil forecast seluruh metode aktif per varian dan pengujian peramalannya, diakhiri analisis metode terbaik. …"
- Langkah 2 "Metode terbaik" **tidak diubah**.

### 4.4 Test FE (Vitest + RTL, tulis dulu)
- `MethodForecastMatrix`: render header `Jan-26 … Des-26`, kolom Varian = kode produk, "—" untuk `FAILED`.
- `MethodMetricsTable`: urutan kolom MAD, MAPE, MFE; baris Average; catatan `n = 6 dari 7`.
- `BestMethodAnalysis`: baris peringkat #1 = `best_method`, peringatan `common` muncul hanya bila `ranking_basis === "common"`, label "diganti planner" saat `method_used !== best_method`.
- `MethodComparisonView`: urutan section mengikuti respons; chip navigasi ada per metode.
- `RunDetail`: tab default "Per metode", `?view=product` membuka tabel lama.
- `formatPeriodLabel` unit test.

---

## 5. Export Excel format thesis (P1)

`build_forecast_xlsx` saat ini hanya sheet "Forecast" (ringkasan per produk). Tambahkan sheet **"Format Thesis"**
yang memakai output `build_method_comparison` yang sama: per metode blok judul → tabel hasil ramalan → tabel
pengujian + Average, lalu blok "Analisis pemilihan metode terbaik". Sheet lama **tidak diubah** (kompatibilitas).
Test: workbook punya 2 sheet; sel judul "1. Metode Random Forest"; baris "Average" ada.

---

## 6. Di luar cakupan
- Mengubah aturan seleksi per produk (`selection.py`) — tetap.
- Grafik per metode (bisa jadi CR berikutnya: small multiples aktual vs forecast per metode).
- Part 2+ thesis (MRP, SS, ROP, dst.) — sudah di langkah 3–5.

## 7. Pertanyaan terbuka untuk Budi
1. Label bulan: `Jan-26 … Des-26` (Indonesia, default) atau `Dec-26` (Inggris, seperti sketsa)?
2. Peringkat level run: tetap MAD → MAPE → MFE atas rata-rata (default), atau MAPE dulu karena skala-bebas?
3. View default langkah 1: "Per metode" (default CR ini) atau "Per produk"?

## 8. Definition of Done
- [x] ✅ Endpoint `method-comparison` + test unit & API hijau (`test_method_comparison.py` 15, `test_method_comparison_api.py` 4: 200/override/404/401); coverage total 96% (sebelumnya 95%), `method_comparison.py` 100%.
- [x] ✅ Langkah 1 menampilkan section 1..N per metode + analisis, sesuai sketsa. ⚠️ D8 diganti seleksi global yang dipakai run; D9 (varian dimenangkan, ✓ per varian) dihapus — keputusan user 23 Nov 2026.
- [x] ✅ Toggle "Per produk" tetap berfungsi persis seperti sebelumnya (test RunDetail lama tetap hijau + 3 test toggle/`?view=`).
- [x] ✅ Run lama / mode manual / metode gagal tampil rapi ("—" + tooltip; `NO_SERIES`, `FAILED`, `run_selection` null → keadaan kosong).
- [x] ✅ `npm run lint`, `tsc --noEmit`, `vitest`, `pytest` hijau (juga Python 3.11).
- [x] ✅ `docs/RECONCILIATION.md` ditambah entri §"Tampilan Hasil Run Per Metode (Format Thesis) — CR v3.7" (keputusan D1–D10 + jawaban pertanyaan terbuka).
- [x] ✅ (P1) Sheet "Format Thesis" di export & tombol Salin.

### Penyimpangan dari spesifikasi
- §3.1 `product_winners` → `product_methods` `{product_id, status, system_method, method_used, is_overridden}`; `methods[].n_products_won` & `rows[].is_product_best` tidak ada (D9 dihapus).
- §3.1 `run_selection` + `criteria`, `n_completed`, `excluded_methods`; `rows[]` + `total`.
- §3.3 test 5 diganti: override planner tidak mengubah `run_selection`; `product_methods` menandai penggantian.
- §4.2 tabel peringkat: kolom "Varian dimenangkan" → "Varian" (jumlah varian yang dirata-rata).
- §4.4 test integrasi ditaruh di `tests/unit/test_method_comparison_api.py` (pola endpoint yang ada).
