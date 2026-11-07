# TODO v3.3 — Sinkronisasi Kode dengan Dokumen Thesis Terbaru (7 Nov 2026)

| | |
|---|---|
| **Baseline repo** | `budipriyoutomo/forecasting-thesis` @ `4a5003a` (Fase 11.0–11.8 ✅) |
| **Acuan** | `Rumus thesis untuk program.docx` (7 Nov), `Simulasi Thesis 2.xlsx`, `docs/REVISI_V2.md`, `claude/CHANGE_REQUEST_v3.3.md` |
| **Branch saran** | `feat/v3.3-thesis-sync` — 1 PR per fase di bawah |
| **Aturan** | TDD (Red → Green → Refactor), migration additive, `pytest` penuh hijau tiap PR (`AGENTS.md` §3) |

Legenda: 🔴 P0 (salah/inkonsisten) · 🟡 P1 (wajib thesis) · 🟢 P2 (rapi-rapi) · ⛔ blocked (menunggu input)

---

## Ringkasan Hasil Cek Repo

| # | Temuan | Lokasi | Prio |
|---|---|---|---|
| 1 | Titik pesan beda di 2 modul: Reorder = `μ_d·L + SS + B`, Proyeksi Stok = `SS + B` | `reorder_service.compute_reorder` vs `stock_projection_service.generate_for_run` (baris `level = …`) | 🔴 |
| 2 | Qty pesan beda di 2 modul: Reorder = `max(MOQ, S − stok)`, Proyeksi = `n × EOQ`. Tabel UI menampilkan **dua-duanya** (`recommended_order_qty` & `eoq_qty`) tanpa penjelasan | `ReorderTable.tsx` | 🔴 |
| 3 | Rumus ROP thesis (heading baru di docx) masih kosong | docx | ⛔ |
| 4 | **Seed demo bukan BOM thesis**: memakai Cup PP / Lid Foil / Sedotan / Karton / Film, padahal thesis memakai Cap (6 warna) + Bottle White + Preform White | `app/scripts/seed_demo_data.py` (`_SHARED_MATERIALS`, `_SHARED_BOM`) | 🔴 untuk thesis |
| 5 | **Data 2025 di seed sintetis** (2024 × 1,12 × wobble), padahal data riil 2025 ada di Excel baris 34–40 | `seed_demo_data.py` (`_DERIVED_YEARS`) | 🔴 untuk thesis |
| 6 | Seed tidak membuat template biaya thesis, kapasitas material, stok awal, kedatangan, pemakaian aktual → pipeline 11.x tidak bisa didemokan dari seed | `seed_demo_data.py` | 🟡 |
| 7 | Rumus MAPE di docx tanpa absolut; kode sudah benar, tapi belum ada test eksplisit "error +/− tidak saling meniadakan" | `tests/unit/test_evaluation.py` | 🟢 |
| 8 | Definisi stock out rate: PRD = berbasis qty, kode = berbasis periode; label UI "Fill Rate" belum memakai istilah docx "Fulfilment rate" | `InventoryMetricsTable.tsx`, `docs/PRD.md` FR-11.3 | 🟡 |
| 9 | `Simulasi Thesis.xlsx` 7 Nov tidak terbaca (nama duplikat di project) | Project files | ⛔ |

---

## Fase 11.9 — Satukan Reorder Point & Qty Pesan 🔴 ✅ (7 Nov 2026, branch `feat/v3.3-thesis-sync`)

> Configurable lewat master data Pengaturan Forecast (pola sama dengan `eoq_method`). Default = perilaku **tabel Reorder** sebelum v3.3. ⚠️ Angka **Proyeksi Stok berubah** untuk semua setting (level `SS + B` → ROP; `n × EOQ` → sesuai policy) — memang tujuan penyatuan; catat di RECONCILIATION (Fase 11.13).

### Keputusan implementasi
- Kebijakan `eoq` = **n × EOQ**, n ≥ 1 terkecil s.d. `stok + n·EOQ ≥ ROP` (bukan 1 × EOQ — kalau pemakaian sebulan > EOQ, proyeksi akan kekurangan stok terus). EOQ ≤ 0 → fallback `order_up_to`. EOQ sudah dibulatkan ke MOQ di `generate_for_run`, tidak dibulatkan ulang.
- Pembanding disatukan: **`stok ≤ ROP`** → pesan (proyeksi dulu pakai `<`).
- `reorder_recommendations` juga menyimpan `order_up_to_level` & `moq_used` → Proyeksi Stok merekonstruksi kebijakan via `order_policy_from_rec(rec)` tanpa hitung ulang. Baris lama (NULL) → `order_up_to`, S = 2·ROP − SS − B, MOQ 0.
- Sumber tunggal: `compute_rop`, `compute_order_qty`, `OrderPolicy` di `reorder_service.py`; `project_stock(opening, receipts, usage, policy, capacity)`.
- UI memakai radio (konsisten dengan opsi EOQ/service level), bukan dropdown.
- ⛔ Rumus S = ROP + μ·L (= 2·μ·L + SS + B) tidak lazim — konfirmasi ke docx bersama rumus ROP.

### Backend
- [x] Migration additive `b5c6d7e8f9a0_v3_3_reorder_policy` (revises `a4b5c6d7e8f9` — **commit migration product_fk_ondelete dulu**): `forecast_settings.rop_formula`, `order_qty_policy` (+ CHECK); `reorder_recommendations.rop_formula_used`, `order_qty_policy_used`, `order_up_to_level`, `moq_used`
- [x] Model, schema (`Literal`), `ForecastSettingsService.rop_formula()` / `order_qty_policy()`, endpoint GET/PUT
- [x] `compute_rop`, `compute_order_qty`, `OrderPolicy`, `order_policy_from_rec`; `compute_reorder` kompatibel (param opsional `formula`, `policy`, `eoq_qty`; `order_up_to_level` di hasil)
- [x] `generate_for_run`: EOQ dihitung sebelum `compute_reorder`, kolom `*_used` terisi
- [x] `stock_projection_service`: titik & qty pesan dari `OrderPolicy`; docstring asumsi lead time < 1 periode
- [x] Schema/API reorder + export xlsx (2 kolom baru di akhir, kolom lama tidak bergeser)

### Test
- [x] `test_reorder_compute.py`, `test_reorder_daily_units.py` (ROP standard L = 7 hari)
- [x] **Baru** `test_reorder_projection_consistency.py` — 2 rumus × 2 policy × MOQ {0, 700}
- [x] `test_stock_projection*.py`, `test_reorder_service.py`, `test_reorder_api.py`, `test_export_service.py`, `test_forecast_settings_*` (422 enum)

### Frontend
- [x] `ForecastSettingsForm`: Rumus titik pesan + Kebijakan qty pesan (+ penjelasan rumus)
- [x] `types/reorder.ts`, `types/forecastSettings.ts`
- [x] `ReorderTable`: kolom tunggal **Qty pesan** + label kebijakan (Kelipatan EOQ / Order-up-to S); **EOQ (info)**; rumus ROP di bawah angka
- [x] Test `ForecastSettingsForm`, `ReorderTable`
- [x] `OverrideForm` — tidak perlu diubah: label qty dikirim lewat prop, override tetap menimpa qty final apa pun policy-nya. **Temuan (pre-existing, di luar v3.3):** `OverrideForm`/`AuditTrail`/`useOverrides` belum dipasang di halaman mana pun → planner belum bisa override dari UI (backend `/overrides` sudah ada)

**Selesai jika:** ROP sama, dan untuk stok yang sama `compute_order_qty` menghasilkan qty yang sama di Reorder & Proyeksi Stok, untuk setiap kombinasi setting — ✅ dibuktikan `test_reorder_projection_consistency.py`.

---

## Fase 11.10 — Kunci Definisi Metrik & Rumus Evaluasi 🟡 ✅ (7 Nov 2026, kecuali ⛔)

- [x] `tests/unit/test_evaluation.py`: `test_mape_error_positif_negatif_tidak_saling_meniadakan` (A=[100,100], F=[90,110] → MAPE 10%, MFE 0) — kode sudah benar, test mengunci
- [x] `tests/unit/test_inventory_metrics_service.py`: `test_definisi_metrik_dikunci_periode_vs_qty` + `test_material_metrics_definisi_sama_dengan_produk` (scope produk & material pakai definisi identik)
- [x] `app/services/inventory_metrics_service.py`: docstring modul + 3 fungsi (sumber: RECONCILIATION §Fase 7, sementara docx belum memuat rumus)
  - Fulfilment rate (β) = 1 − Σ kekurangan ÷ Σ demand
  - Stock out rate = periode kekurangan ÷ jumlah periode
  - Service level (α) = 1 − stock out rate
- [x] `InventoryMetricsTable.tsx`: header **"Service Level (α)"**, **"Fulfilment Rate (β)"**, **"Stock Out Rate"** + tooltip rumus; field API tetap `fill_rate` (tidak breaking); test mapping kolom
- [x] Export PDF metrik: header "Fill rate" → "Fulfilment" (ASCII; font PDF core tidak punya β)
- [ ] PRD FR-11.3 masih menulis "fill rate" → dikerjakan di Fase 11.13
- [ ] ⛔ Bila docx mendefinisikan stock out rate berbasis qty → tambah opsi di Pengaturan Forecast, jangan ganti diam-diam

---

## Fase 11.11 — Seed & Golden Test Data Thesis 🔴 🟡 sebagian (7 Nov 2026)

> Sumber: `~/Downloads/Simulasi Thesis.xlsx` (7 Nov, 108 KB) — sheet *Bab I Plan vs Forecast* & *Pengumpulan Data*. `Simulasi Thesis.xlsx` di root repo (gitignored) masih versi **4 Jul**. Konstanta murni di `app/scripts/thesis_data.py` (sumber tunggal, juga dipakai profil demo).

### Seed (`app/scripts/seed_demo_data.py` + `thesis_data.py`)
- [x] `--profile thesis` (default `demo` tetap untuk UI/dev); profil tidak dikenal → `ValueError`
- [x] Material thesis `CAP-BLUE/RED/PURPLE/WHITE/GREY/YELLOW`, `BTL-WHITE`, `PRF-WHITE`, lead time 7 hari (Excel "Leadtime Pemesanan Material")
- [x] BOM level 1: 6 SKU → 1 Cap warna + 1 Bottle White (12 baris)
- [x] BOM level 2 (`material_components`): Bottle White → 1 Preform White
- [x] Mapping "Yoghurt SB" — **keputusan user 7 Nov: KBYST 200 & KBYSR 200 sama-sama Cap Red** + Bottle White → 7 SKU, 14 baris BOM; Cap Red jadi material bersama 2 SKU
- [x] Demand 2024 & **2025 riil** (baris 11–17 & 34–40, 12 bulan × 7 SKU); 2024 di seed lama sudah identik dengan Excel 7 Nov. Profil thesis = 24 periode riil; profil demo = 2023 & H1 2026 sintetis + 2024–2025 riil
- [x] Template biaya thesis — 6 elemen sesuai Excel (TK langsung 3.972.202 × 2, listrik, lampu, forklift, handpallet, pallet plastik), total Rp 17.567.052/bln = Rp 210.804.626/thn ✅ cocok kolom P/Q. Di-seed **tidak aktif**: S (biaya pesan), H, i (%) belum ada di Excel
  - Catatan: Excel 7 Nov **tidak** memuat rak, fasilitas gudang, atau perawatan forklift (yang direncanakan di TODO awal) — forklift masuk sebagai depresiasi 15 thn
- [x] Kapasitas Preform: 346 pallet × 1 CTN × 16.056 pcs = 5.555.376 pcs (`item_type = material`)
- [x] Kapasitas **Cap** = satu angka group (171 pallet × 25 CTN × 3.000 = 12.825.000 pcs) untuk 6 warna — **keputusan user 7 Nov: tidak di-seed** sampai penulis memberi angka per warna (utilisasi Cap tampil "—"). Referensi di `CAP_GROUP_CAPACITY`
- [ ] ⛔ Lead time Bottle White tidak tercantum — sementara 7 hari (= Preform)
- [ ] ⛔ Harga material, MOQ, harga jual, stok awal, kedatangan, pemakaian aktual — tidak ada di Excel 7 Nov
- [x] `tests/unit/test_seed_demo_data.py` (+ profil thesis, idempoten) & **baru** `tests/unit/test_thesis_data.py` (total baris 18 Excel, sel sampel 2025, kapasitas, biaya kolom Q)

### Golden test (`tests/integration/test_thesis_golden.py` — baru, kerangka)
- [x] Fixture 7 SKU × 24 bulan + BOM thesis
- [x] MRP Bottle White Jan 2025 = 1.220.052 (Σ planning F34:F40, 7 SKU); Cap Red = KBYST + KBYSR; BOM tree 3 level; total biaya simpan = Excel
- [ ] ⛔ 7 assertion di-skip (alasan tampil di `pytest -rs`) sampai `docs/thesis_golden.xlsx` ada:
  - [ ] MAD/MFE/MAPE + metode pemenang KBYPL 200 · [ ] α ES · [ ] SS & ROP · [ ] EOQ klasik + TC · [ ] stock akhir & utilisasi · [ ] shortage cost · [ ] saran i (%)

---

## Fase 11.12 — Cek Ulang Excel 7 Nov 🟡 sebagian

- [ ] Simpan versi 7 Nov ke root repo (gitignored) menggantikan versi 4 Jul; rename di project Claude → `Simulasi Thesis 3.xlsx`; hapus duplikat docx 26 Okt
- [x] Mapping SB → lihat 11.11 (KBYST & KBYSR → Cap Red, keputusan user)
- [x] Data kapasitas material → Preform & Cap (group) ada; Bottle tidak
- [x] **Juni 2025 = 0 untuk 6 dari 7 SKU** (hanya KBYPL 186.840) — keputusan user 7 Nov: dipakai apa adanya (dianggap tidak produksi)
- [ ] ⛔ `#REF!` tabel gap 2025 (C5:N5) masih ada di Excel 7 Nov — perbaikan di Excel oleh penulis (angka 26%/33% di PRD bergantung ke sini)
- [ ] Contoh hitung ROP/service level — tidak ditemukan di Excel 7 Nov (sheet: Kerangka Pemikiran, Tahapan, Penelitian Terdahulu, Plan vs Forecast, Posisi Penelitian, Pengumpulan Data, Flow Chart, White Box)
- [x] White Box tahap 5 menulis "Service level (%) / Fulfillment rate" sebagai satu metrik — **keputusan user 7 Nov: tampilkan keduanya** (α & β terpisah seperti sekarang); penulis memilih yang dikutip di bab hasil

---

## Fase 11.13 — Dokumen 🟢 ✅ (7 Nov 2026, kecuali docx)

- [x] `docs/REVISI_V2.md` §9 "Delta 7 Nov 2026" (`claude/CHANGE_REQUEST_v3.3.md` tidak ada di repo → diringkas dari TODO ini & hasil Fase 11.9–11.11)
- [x] `docs/RECONCILIATION.md` → "Rekonsiliasi v3.3" (11.9 kebijakan ROP & qty pesan, 11.10 metrik, 11.11 seed)
- [x] `docs/PRD.md` — ROP & qty pesan ada di **FR-4.2/4.3** (+ FR-4.3a baru), bukan FR-5 (FR-5 = override); FR-11.3 definisi metrik; FR-12.1/12.8/12.9
- [x] `docs/ARCHITECTURE.md` §4 (`forecast_settings`, `reorder_recommendations`), §6.8 (sumber tunggal ROP/qty), §6.10 (migration & rumus proyeksi)
- [x] `AGENTS.md` checklist PR: rumus titik pesan/qty pesan hanya dari `reorder_service`
- [x] `docs/TASK_BREAKDOWN.md` §13 Fase 11.9–11.13
- [ ] ⛔ Docx thesis (penulis): MAPE pakai |…|, isi rumus ROP, service level, fulfilment rate, stock out rate, asumsi lead time < 1 periode

---

## Fase 11.14 — UI Override Planner ✅ (7 Nov 2026, kecuali forecast)

> Temuan: `OverrideForm`/`AuditTrail`/`useOverrides` & endpoint `/overrides` sudah ada sejak Fase 6, tapi tidak dipasang di halaman mana pun, response reorder/forecast tidak membawa `id`, dan override tidak dipakai di mana pun.

- [x] `ReorderRecommendationOut.id` + `override_qty/override_reason/override_at` (override yang berlaku)
- [x] `overrides.run_id/material_id` (migration `c6d7e8f9a0b1`, additive + backfill); `GET /overrides/reorder?run_id&material_id`
- [x] `ReorderTable`: kolom **Aksi** "Override"; qty override tampil di samping qty sistem
- [x] **Baru** `ReorderOverrideDialog` (form qty + alasan wajib + riwayat per run+material), dipasang di halaman run
- [x] Proyeksi Stok `proposed`: pesanan periode pertama = qty override (baseline tidak kena); export xlsx 2 kolom akhir
- [x] Keputusan user: tampilkan + pakai di proyeksi; riwayat per (run, material); forecast override ditunda
- [ ] Override **hasil forecast** via UI — ditunda (keputusan user)
- [ ] `replace_for_run` masih menghapus baris lama (AGENTS §6) — riwayat aman via konteks; versioning rekomendasi bila dibutuhkan nanti

---

## Urutan Kerja yang Disarankan

| Urutan | Fase | Bisa mulai sekarang? | Estimasi |
|---|---|---|---|
| 1 | 11.9 Satukan ROP & qty pesan | ✅ Ya (configurable) | 1–1,5 hari |
| 2 | 11.10 Definisi metrik + label UI | ✅ Ya (sebagian) | 0,5 hari |
| 3 | 11.11 Seed thesis (tanpa bagian ⛔) + golden test kerangka | ✅ Ya | 1,5 hari |
| 4 | 11.12 Cek Excel 7 Nov | ⛔ Rename file dulu | 0,5 hari |
| 5 | 11.11 bagian ⛔ + golden test angka final | Setelah 4 | 1 hari |
| 6 | 11.13 Dokumen | Paralel | 0,5 hari |