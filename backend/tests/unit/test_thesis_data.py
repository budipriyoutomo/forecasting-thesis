"""
Fase 11.11 (v3.3) — konstanta data thesis (`app/scripts/thesis_data.py`).

Sumber: `Simulasi Thesis.xlsx` versi 7 Nov 2026 — sheet "Bab I Plan vs Forecast"
(baris 11–17 = 2024, 34–40 = 2025) dan "Pengumpulan Data" (BOM, kapasitas gudang,
lead time, elemen biaya penyimpanan). Angka di sini dicek ulang terhadap total/kolom
hitung yang ADA di Excel, bukan dihitung ulang dari kode.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.scripts.thesis_data import (
    CAP_GROUP_CAPACITY,
    THESIS_BOM,
    THESIS_COMPONENTS,
    THESIS_COST_ITEMS,
    THESIS_DEMAND_2024,
    THESIS_DEMAND_2025,
    THESIS_MATERIAL_CAPACITY,
    THESIS_MATERIALS,
    THESIS_PRODUCT_CODES,
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
    (cap,) = THESIS_MATERIAL_CAPACITY
    assert cap.material_code == "PRF-WHITE"
    inp = CapacityInput(capacity_mode=cap.capacity_mode, pallet_qty=cap.pallet_qty,
                        dus_per_pallet=cap.dus_per_pallet, pcs_per_dus=cap.pcs_per_dus)
    dus, pcs = compute_effective_capacity(inp, "PCS")
    assert (dus, pcs) == (346, 5_555_376)


def test_kapasitas_group_cap_hanya_referensi():
    # Excel: Cap 171 pallet = 4.275 carton = 12.825.000 pcs — SATU angka untuk 6 warna.
    assert CAP_GROUP_CAPACITY == {"pallet": 171, "ctn_per_pallet": 25, "pcs_per_ctn": 3000, "pcs": 12_825_000}
    assert CAP_GROUP_CAPACITY["pallet"] * CAP_GROUP_CAPACITY["ctn_per_pallet"] * CAP_GROUP_CAPACITY["pcs_per_ctn"] == 12_825_000


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
