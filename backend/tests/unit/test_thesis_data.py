"""
Fase 11.11 (v3.3) — konstanta data thesis (`app/scripts/thesis_data.py`).

Sumber: `Simulasi Thesis.xlsx` versi 7 Nov 2026 — sheet "Bab I Plan vs Forecast"
(baris 11–17 = 2024, 34–40 = 2025) dan "Pengumpulan Data" (BOM, kapasitas gudang,
lead time, elemen biaya penyimpanan). Angka di sini dicek ulang terhadap total/kolom
hitung yang ADA di Excel, bukan dihitung ulang dari kode.
"""
from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pandas as pd
import pytest

from app.scripts.thesis_data import (
    CAP_GROUP_CAPACITY,
    THESIS_ACTIVE_EXOG,
    THESIS_BOM,
    THESIS_COMPONENTS,
    THESIS_COST_ITEMS,
    THESIS_DEMAND_2024,
    THESIS_DEMAND_2025,
    THESIS_EXTERNAL_VARIABLES,
    THESIS_MATERIAL_CAPACITY,
    THESIS_MATERIALS,
    THESIS_PRODUCT_CODES,
    thesis_exog_series,
)
from app.services.cost_template_service import item_monthly_cost
from app.services.warehouse_service import CapacityInput, compute_effective_capacity

CAPS = {"CAP-BLUE", "CAP-RED", "CAP-PURPLE", "CAP-WHITE", "CAP-GREY", "CAP-YELLOW"}


def test_demand_2024_2025_lengkap_12_bulan_7_sku():
    for data in (THESIS_DEMAND_2024, THESIS_DEMAND_2025):
        assert set(data) == set(THESIS_PRODUCT_CODES)
        assert all(len(rows) == 12 and all(len(r) == 3 for r in rows) for rows in data.values())


@pytest.mark.parametrize(
    "month, totals",
    [  # Excel baris 18 (Total 2024): (Forecast, Planning, Actual)
        (0, (1_712_856, 1_665_720, 1_611_552)),
        (1, (1_407_432, 1_336_800, 1_295_832)),
        (2, (1_572_936, 1_549_176, 1_481_304)),
        (3, (1_525_560, 1_240_152, 1_293_744)),
    ],
)
def test_total_2024_sama_dengan_baris_total_excel(month, totals):
    got = tuple(sum(THESIS_DEMAND_2024[c][month][k] for c in THESIS_PRODUCT_CODES) for k in range(3))
    assert got == totals


def test_demand_2025_sampel_sel_excel():
    assert THESIS_DEMAND_2025["KBYPL 200"][0] == (141300, 188400, 186696)  # E34:G34
    assert THESIS_DEMAND_2025["KBYMG 200"][3] == (165858, 94776, 93120)  # Z40:AB40
    assert THESIS_DEMAND_2025["KBYSR 200"][11] == (47136, 0, 0)


def test_material_thesis_cap_bottle_preform_lead_time_7_hari():
    codes = {m.code for m in THESIS_MATERIALS}
    assert codes == CAPS | {"BTL-WHITE", "PRF-WHITE"}
    # Excel "Leadtime Pemesanan Material": Preform & Cap = 7 hari.
    assert all(m.lead_time_days == 7 for m in THESIS_MATERIALS)


def test_bom_level_1_cap_warna_plus_bottle_white():
    mapping = {
        "KBYPL 200": "CAP-BLUE",
        "KBYST 200": "CAP-RED",  # "Yoghurt SB" — keputusan user 7 Nov: KBYST & KBYSR
        "KBYSR 200": "CAP-RED",  # sama-sama Cap Red (asumsi, lihat modul)
        "KBYBB 200": "CAP-PURPLE",
        "KBYLY 200": "CAP-WHITE",
        "KBYBF 200": "CAP-GREY",
        "KBYMG 200": "CAP-YELLOW",
    }
    by_product = {}
    for line in THESIS_BOM:
        by_product.setdefault(line.product_code, set()).add((line.material_code, line.qty_per_unit))
    assert by_product == {p: {(cap, 1), ("BTL-WHITE", 1)} for p, cap in mapping.items()}
    assert set(by_product) == set(THESIS_PRODUCT_CODES)  # 7 SKU semua punya BOM


def test_bom_level_2_bottle_ke_preform():
    assert [(c.parent_code, c.component_code, c.qty_per_unit) for c in THESIS_COMPONENTS] == [
        ("BTL-WHITE", "PRF-WHITE", 1)
    ]


def test_kapasitas_preform_pallet_ke_pcs():
    # Excel: Preform 346 pallet = 346 carton = 5.555.376 pcs → 1 CTN/pallet, 16.056 pcs/CTN
    cap = next(c for c in THESIS_MATERIAL_CAPACITY if c.material_group == "preform")
    inp = CapacityInput(capacity_mode=cap.capacity_mode, pallet_qty=cap.pallet_qty,
                        dus_per_pallet=cap.dus_per_pallet, pcs_per_dus=cap.pcs_per_dus)
    dus, pcs = compute_effective_capacity(inp, "PCS")
    assert (dus, pcs) == (346, 5_555_376)


def test_kapasitas_group_cap_satu_angka_untuk_6_warna():
    # Excel: Cap 171 pallet = 4.275 carton = 12.825.000 pcs — SATU angka untuk 6 warna.
    # Sejak 19 Nov 2026 kapasitas per grup material → di-seed sebagai grup "cap".
    assert CAP_GROUP_CAPACITY == {"pallet": 171, "ctn_per_pallet": 25, "pcs_per_ctn": 3000, "pcs": 12_825_000}
    cap = next(c for c in THESIS_MATERIAL_CAPACITY if c.material_group == "cap")
    inp = CapacityInput(capacity_mode=cap.capacity_mode, pallet_qty=cap.pallet_qty,
                        dus_per_pallet=cap.dus_per_pallet, pcs_per_dus=cap.pcs_per_dus)
    assert compute_effective_capacity(inp, "PCS") == (4275, CAP_GROUP_CAPACITY["pcs"])
    # grup kapasitas harus cocok dengan category material thesis
    assert {c.material_group for c in THESIS_MATERIAL_CAPACITY} <= {m.category for m in THESIS_MATERIALS}


@pytest.mark.parametrize(
    "name, monthly",
    [  # Excel "Elemen Biaya Penyimpanan" kolom Q (Biaya/Bulan)
        ("Tenaga Kerja Langsung (Operator)", Decimal("7944404")),
        ("Listrik (1.392 kWh/bulan)", Decimal("1619870.4")),
        ("Lampu", Decimal("1388888.8889")),
        ("Forklift", Decimal("2222222.2222")),
        ("Handpallet", Decimal("83333.3333")),
        ("Pallet Plastik", Decimal("4308333.3333")),
    ],
)
def test_biaya_penyimpanan_bulanan_sama_dengan_excel(name, monthly):
    item = next(i for i in THESIS_COST_ITEMS if i.name == name)
    row = SimpleNamespace(**{"salvage_value": 0, "period_basis": "monthly", **item.__dict__})
    assert item_monthly_cost(row) == monthly


# ── CR v3.4 §4.7 — variabel eksternal thesis (sheet "Pengumpulan Data" kolom S–AV) ──

_BY_CODE = {v.code: v for v in THESIS_EXTERNAL_VARIABLES}


def test_variabel_aktif_sesuai_keputusan_penulis_20_nov():
    """8 variabel CR v3.4 §5 + seluruh kategori Perilaku Konsumen & Ekonomi, termasuk turunan
    permintaan (keputusan penulis 20 Nov 2026, leakage sudah diperingatkan)."""
    assert set(THESIS_ACTIVE_EXOG) == {
        "harga_efektif", "harga_kompetitor", "diskon_kompetitor", "suhu",
        "idul_fitri", "hari_libur_sekolah", "gt_yogurt", "inflasi",
        "tbi", "gt_makanan_sehat", "gt_probiotik", "perubahan_harga", "pendapatan",
        "permintaan", "perubahan_permintaan", "ep",
    }
    assert {v.code for v in THESIS_EXTERNAL_VARIABLES if v.is_active} == set(THESIS_ACTIVE_EXOG)


def test_variabel_turunan_permintaan_aktif_dengan_peringatan_leakage():
    """Permintaan (AM) = Σ planning bulan yang sama (korelasi 1,00 dengan Σ actual) → leakage.
    Diaktifkan atas keputusan penulis; peringatan wajib tetap tertulis di deskripsi."""
    for code in ("permintaan", "perubahan_permintaan", "ep"):
        assert _BY_CODE[code].is_active is True
        assert "LEAKAGE" in _BY_CODE[code].description
        assert _BY_CODE[code].horizon_rule == "zero_fill"
    assert "harga_promo" not in _BY_CODE


def test_semua_variabel_global_dan_flag_bernilai_0_1():
    for v in THESIS_EXTERNAL_VARIABLES:
        assert v.scope == "global"
        if v.value_type == "flag":
            assert set(thesis_exog_series(v.code, "realisasi").values()) <= {Decimal(0), Decimal(1)}, v.code


@pytest.mark.parametrize(
    "code,period,expected",
    [
        ("suhu", date(2024, 1, 1), Decimal("27.2")),
        ("gt_yogurt", date(2024, 4, 1), Decimal("40.33")),  # sel teks "40,33\t"
        ("harga_efektif", date(2024, 6, 1), Decimal("8200")),  # harga promo berlaku
        ("harga_efektif", date(2024, 5, 1), Decimal("9900")),  # harga normal
        ("harga_kompetitor", date(2024, 6, 1), Decimal("6900")),
        ("inflasi", date(2024, 6, 1), Decimal("-0.0008")),
        ("diskon_produk", date(2024, 6, 1), Decimal("0.1717")),  # Numeric(18,4)
        ("musim_hujan", date(2024, 1, 1), Decimal(1)),
        ("musim_kemarau", date(2024, 6, 1), Decimal(1)),
        ("musim_hujan", date(2024, 4, 1), Decimal(0)),  # Peralihan → keduanya 0
        ("musim_kemarau", date(2024, 4, 1), Decimal(0)),
        ("curah_hujan", date(2024, 4, 1), Decimal(3)),
    ],
)
def test_nilai_exog_sampel_sel_excel(code, period, expected):
    assert thesis_exog_series(code, "realisasi")[period] == expected


def test_sel_na_dan_harga_kosong_tidak_jadi_angka():
    real = thesis_exog_series("hari_promo", "realisasi")
    assert date(2024, 6, 1) not in real  # "NA" di Excel
    # AN Nov–Des 2026 = 0 karena harga normal kosong (artefak rumus) → bukan harga 0
    assert date(2026, 11, 1) not in thesis_exog_series("harga_efektif", "realisasi")


def test_idul_fitri_bergeser_tiap_tahun():
    s = thesis_exog_series("idul_fitri", "realisasi")
    assert sorted(p for p, v in s.items() if v == 1) == [
        date(2024, 4, 1), date(2025, 3, 1), date(2025, 4, 1), date(2026, 3, 1),
    ]


def test_skenario_realisasi_2026_sampai_oktober():
    s = thesis_exog_series("suhu", "realisasi")
    assert max(s) == date(2026, 10, 1)
    assert len(s) == 34


def test_skenario_asumsi_aturan_per_variabel():
    """CR v3.4 §5 no. 6–7: hanya variabel known-in-advance yang memakai realisasi 2026."""
    real = {c: thesis_exog_series(c, "realisasi") for c in ("suhu", "inflasi", "harga_kompetitor", "harga_efektif")}
    suhu = thesis_exog_series("suhu", "asumsi")
    assert suhu[date(2026, 1, 1)] == (real["suhu"][date(2024, 1, 1)] + real["suhu"][date(2025, 1, 1)]) / 2
    inflasi = thesis_exog_series("inflasi", "asumsi")
    assert {inflasi[date(2026, m, 1)] for m in range(1, 13)} == {real["inflasi"][date(2025, 12, 1)]}
    kompetitor = thesis_exog_series("harga_kompetitor", "asumsi")
    assert kompetitor[date(2026, 6, 1)] == real["harga_kompetitor"][date(2025, 12, 1)]
    harga = thesis_exog_series("harga_efektif", "asumsi")
    assert harga[date(2026, 6, 1)] == real["harga_efektif"][date(2026, 6, 1)]  # rencana harga diketahui
    assert harga[date(2026, 11, 1)] == real["harga_efektif"][date(2025, 11, 1)]  # kosong di Excel → bulan sama 2025
    assert _BY_CODE["harga_kompetitor"].horizon_rule == "last_value"


def test_histori_2024_2025_sama_di_kedua_skenario():
    for code in THESIS_ACTIVE_EXOG:
        real, asumsi = thesis_exog_series(code, "realisasi"), thesis_exog_series(code, "asumsi")
        assert {p: v for p, v in real.items() if p.year < 2026} == {p: v for p, v in asumsi.items() if p.year < 2026}


def test_variabel_aktif_lolos_usable_exog_horizon_12_skenario_asumsi():
    """Demand thesis 24 bulan + horizon 12 → tidak ada variabel aktif yang di-drop engine."""
    from app.services.forecasting.engines._ml import usable_exog

    idx = pd.date_range("2024-01-01", periods=36, freq="MS")
    exog = pd.DataFrame(
        {c: pd.Series({pd.Timestamp(p): float(v) for p, v in thesis_exog_series(c, "asumsi").items()}) for c in THESIS_ACTIVE_EXOG}
    )
    used, dropped = usable_exog(exog, idx[:24], idx[24:])
    assert dropped == {}
    assert set(used.columns) == set(THESIS_ACTIVE_EXOG)


def test_skenario_tidak_dikenal_ditolak():
    with pytest.raises(ValueError):
        thesis_exog_series("suhu", "oracle")



# ── Keputusan penulis 20 Nov 2026: error / kosong → 0 untuk TBI, Pendapatan, Ep ──


@pytest.mark.parametrize("scenario", ["asumsi", "realisasi"])
def test_isi_nol_36_bulan_kedua_skenario(scenario):
    for code in ("tbi", "pendapatan", "ep", "permintaan", "perubahan_permintaan"):
        s = thesis_exog_series(code, scenario)
        assert len(s) == 36, code
    assert thesis_exog_series("permintaan", scenario)[date(2024, 1, 1)] == Decimal("1665720")
    assert thesis_exog_series("permintaan", scenario)[date(2026, 11, 1)] == 0  # kosong di Excel
    assert thesis_exog_series("perubahan_permintaan", scenario)[date(2024, 1, 1)] == 0  # "-"
    assert thesis_exog_series("pendapatan", scenario)[date(2024, 1, 1)] == 0  # "-" di Excel
    assert thesis_exog_series("pendapatan", scenario)[date(2024, 2, 1)] == Decimal("3040000")
    assert thesis_exog_series("tbi", scenario)[date(2024, 2, 1)] == 0
    assert thesis_exog_series("ep", scenario)[date(2024, 2, 1)] == 0  # #DIV/0! di Excel
    assert thesis_exog_series("ep", scenario)[date(2024, 6, 1)] == Decimal("-4.9388")


def test_perubahan_harga_rumus_titik_tengah_dari_harga_efektif():
    """AO = (Hₜ − Hₜ₋₁) / ((Hₜ + Hₜ₋₁)/2); bulan pertama 0. Dihitung dari harga_efektif skenario
    yang sama supaya horizon konsisten (AO Excel Nov–Des 2026 rusak karena AN = 0)."""
    s = thesis_exog_series("perubahan_harga", "realisasi")
    assert s[date(2024, 1, 1)] == 0
    assert s[date(2024, 5, 1)] == 0
    assert s[date(2024, 6, 1)] == Decimal("-0.1878")  # Excel AO10 = -0.18784…
    asumsi = thesis_exog_series("perubahan_harga", "asumsi")
    assert len(asumsi) == 36


def test_tbi_dan_pendapatan_tidak_konstan_di_histori():
    """Diisi 0 tapi tetap bervariasi di 2024–2025 → tidak di-drop `constant`."""
    for code in ("tbi", "pendapatan"):
        hist = {v for p, v in thesis_exog_series(code, "asumsi").items() if p.year < 2026}
        assert len(hist) > 1, code
