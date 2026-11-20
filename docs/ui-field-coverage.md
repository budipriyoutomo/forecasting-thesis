# UI Field Coverage — CR v3.6

Checklist: setiap field respons backend yang relevan untuk keputusan PPIC punya tempat di UI.
Kolom "Test" menunjuk test yang memastikan field itu tetap terlihat.

## `DashboardSummary` (`GET /dashboard/summary`) — `app/(dashboard)/dashboard/page.tsx`

| Field | Tempat di UI | Test |
|---|---|---|
| `n_materials` | Tile reorder ("dari N material"), kartu Status reorder | `dashboard/__tests__/page.test.tsx` |
| `latest_run.run_id` | Tombol "Lihat detail run", link tile/bar | ✅ |
| `latest_run.status`, `n_products`, `n_completed`, `n_failed` | Kartu Run terakhir | ✅ |
| `latest_run.created_at`, `created_by` | Deskripsi kartu Run terakhir | ✅ |
| `latest_run.n_pending_selection` | CTA "Pilih metode untuk N produk", Butuh perhatian | ✅ |
| `latest_run.avg_mad`, `avg_mfe`, `avg_mape` | Tile akurasi: metrik rata-rata terkecil + namanya; dua lainnya di hint | ✅ |
| `latest_run.avg_mase` | **Sengaja tidak ditampilkan** (21 Nov 2026: hanya MAD, MFE, MAPE) | ✅ |
| `latest_run.total_inventory_cost` | Tile TIC | ✅ |
| `latest_run.total_inventory_cost_baseline`, `savings_pct` | Hint tile TIC | ✅ |
| `reorder_status_counts.*` | Tile "Material perlu reorder" (urgent) + bar bertumpuk | ✅ |
| `n_recent_overrides` | Butuh perhatian | ✅ |
| `warehouse.is_within_capacity`, `n_products_over`, `n_products_checked` | Kartu Kapasitas gudang | ✅ |
| `warehouse.products_over[]` | Daftar maks 5 + "Lihat semua" | ✅ |
| `inventory_metrics[scope].*` | Tabel Kinerja inventory; α forecastiq di tile | ✅ |
| `attention.*` | Kartu Butuh perhatian | ✅ |

## `ReorderRecommendation` — `ReorderTable` + `ReorderDetail` (Sheet "Rincian")

Semua field di `types/reorder.ts` dicek satu per satu oleh
`components/dashboard/__tests__/ReorderTable.test.tsx` → "ReorderDetail — semua field".
Kolom inti tabel: Material · Stok dipakai · Safety stock (+ nilai sistem & badge adjust) ·
Service level efektif (vs target) · Reorder point (+ rumus) · Qty pesan · Status (+ catatan data) · Biaya.
Buffer & EOQ: tersembunyi default, bisa ditampilkan lewat menu "Kolom", selalu ada di Rincian.

## `ForecastResult` / `ForecastCandidate` — `ProductResultsTable` + `ProductResultSheet`

| Field | Tempat | Test |
|---|---|---|
| `status`, `selection_status` | Badge status (tabel & Sheet), filter | `ForecastResults.test.tsx` |
| `status_reason` | Alert produk gagal + langkah perbaikan | ✅ |
| `method_used`, `selection_mode`, `selection_reason` | Kolom Metode & Sumber pilihan, header Sheet | ✅ |
| `mad`, `mfe`, `mape` (result & kandidat) | Kolom tabel ringkasan; tab Perbandingan metode (sesuai checkbox, tooltip definisi) | ✅ `CandidatesTable.test.tsx` |
| `mse`, `mase` | **Sengaja tidak ditampilkan** (21 Nov 2026) | ✅ |
| `forecast` | Total & rata-rata/bulan (tabel, Sheet), tab Angka, grafik | ✅ |
| `history` | Grafik histori → forecast | `ForecastChart.test.ts` |
| `explanation` | Tab Ringkasan | — |
| `hyperparameters` (α, exog) | Header Sheet (α), tab Faktor | ✅ |
| `feature_importance` | Tab Faktor | `FeatureImportance.test.tsx` |
| `metrics` (avg/trend) | Tidak ditampilkan langsung — diganti total & rata-rata dari `forecast` | — |

## `ForecastRunListItem` (`GET /forecast/runs`) — `RunsTable`

`created_at`, `created_by`, `horizon`, `n_products/n_completed/n_failed`, `status`,
`n_pending_selection`, `has_planning`, `run_id` (link) — `app/(dashboard)/forecast/__tests__/page.test.tsx`.

## `ProductDemandCoverage` (`GET /products/demand-coverage`) — `ProductPicker`

`n_periods` (+ tanda < minimal 12), `last_period` — `ProductPicker.test.tsx`.
