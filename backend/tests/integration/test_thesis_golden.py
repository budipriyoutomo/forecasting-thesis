"""
Golden test data thesis (Fase 11.11, v3.3) — KERANGKA.

Fixture: 7 SKU × 24 bulan (2024–2025 riil) + BOM thesis dari `app/scripts/thesis_data.py`
(sumber: `Simulasi Thesis.xlsx` 7 Nov 2026). Angka yang di-assert adalah angka yang ADA
di Excel atau dihitung tangan dari sel Excel (ditulis di komentar) — bukan output kode.

Bagian yang butuh lembar hitung manual (`docs/thesis_golden.xlsx`, belum ada) di-skip
dengan alasan ⛔ supaya daftar sisa pekerjaan terlihat di output pytest.
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.scripts.seed_demo_data import THESIS_PROFILE, build_demand_series
from app.scripts.thesis_data import (
    THESIS_BOM,
    THESIS_COMPONENTS,
    THESIS_COST_ITEMS,
    THESIS_MATERIALS,
    THESIS_PRODUCT_CODES,
)
from app.services.bom_service import BomLine, breakdown_requirements_series
from app.services.cost_template_service import summarize_template
from app.services.material_component_service import build_bom_tree

GOLDEN_PENDING = "⛔ menunggu lembar hitung manual docs/thesis_golden.xlsx (TODO-v3 Fase 11.11)"


@pytest.fixture(scope="module")
def planning_series() -> dict[str, list[float]]:
    """Deret PLANNING 24 bulan per SKU (dasar MRP = rencana produksi × BOM, White Box no. 2/3)."""
    return {
        code: [float(p.planning) for p in build_demand_series(code, THESIS_PROFILE)]
        for code in THESIS_PRODUCT_CODES
    }


@pytest.fixture(scope="module")
def bom_lines() -> list[BomLine]:
    return [BomLine(b.product_code, b.material_code, b.qty_per_unit) for b in THESIS_BOM]


def test_fixture_7_sku_24_bulan(planning_series):
    assert len(planning_series) == 7
    assert all(len(v) == 24 for v in planning_series.values())


def test_mrp_bottle_white_januari_2025(planning_series, bom_lines):
    # Planning Jan 2025 (Excel F34:F40), 7 SKU:
    # 188.400 + 164.928 + 235.752 + 47.124 + 300.024 + 94.272 + 189.552 = 1.220.052
    req = breakdown_requirements_series(planning_series, bom_lines)
    assert req["BTL-WHITE"][12] == 1_220_052
    assert req["CAP-BLUE"][12] == 188_400  # KBYPL 200 saja
    assert req["CAP-RED"][12] == 164_928 + 94_272  # KBYST + KBYSR (Cap Red bersama)


def test_bom_tree_3_level_preform_di_bawah_bottle():
    mats = {m.code: SimpleNamespace(id=m.code, code=m.code, name=m.name, unit=m.unit) for m in THESIS_MATERIALS}
    comps = {
        c.parent_code: [SimpleNamespace(id=f"c-{c.component_code}", component_material_id=c.component_code,
                                        qty_per_unit=c.qty_per_unit)]
        for c in THESIS_COMPONENTS
    }
    lines = [SimpleNamespace(material_id=b.material_code, qty_per_unit=b.qty_per_unit)
             for b in THESIS_BOM if b.product_code == "KBYPL 200"]
    tree = build_bom_tree(SimpleNamespace(id="p", code="KBYPL 200", name="KIN Yogurt Original"), lines, mats, comps)
    bottle = next(n for n in tree["children"] if n["code"] == "BTL-WHITE")
    assert [(c["code"], c["level"], c["purchased"]) for c in bottle["children"]] == [("PRF-WHITE", 2, False)]


def test_biaya_penyimpanan_total_sama_dengan_excel():
    # Σ kolom P (Biaya/Tahun) Excel: 95.332.848 + 19.438.444,8 + 16.666.666,67 + 26.666.666,67
    #                              + 1.000.000 + 51.700.000 = 210.804.626,13
    items = [SimpleNamespace(**i.__dict__) for i in THESIS_COST_ITEMS]
    summary = summarize_template(items, total_capacity_dus=0)
    assert float(summary.total_overhead_monthly) == pytest.approx(7_944_404 + 1_619_870.4)
    assert float(summary.total_annual) == pytest.approx(210_804_626.13, abs=0.01)
    assert summary.total_monthly == Decimal("17567052.1777")


@pytest.mark.skip(reason=GOLDEN_PENDING)
def test_mad_mfe_mape_dan_metode_pemenang_kbypl():
    """MAD/MFE/MAPE tiap metode + pemenang untuk KBYPL 200."""


@pytest.mark.skip(reason=GOLDEN_PENDING)
def test_alpha_es_terpilih_kbypl():
    """α ES terpilih (grid thesis) untuk KBYPL 200."""


@pytest.mark.skip(reason=GOLDEN_PENDING)
def test_ss_dan_rop_satu_material_bulanan_ke_harian():
    """SS & ROP Cap Blue, L = 7 hari, μ/σ bulanan → harian (rumus ROP docx masih kosong)."""


@pytest.mark.skip(reason=GOLDEN_PENDING + " + harga material & i (%) belum ada di Excel")
def test_eoq_klasik_dan_tc_satu_material():
    """EOQ √(2AS/iC) + TC untuk 1 material."""


@pytest.mark.skip(reason=GOLDEN_PENDING + " + stok awal/kedatangan belum ada di Excel")
def test_stock_akhir_dan_utilisasi_satu_periode():
    """Stock akhir & utilisasi Preform (kapasitas 5.555.376 pcs) untuk 1 periode."""


@pytest.mark.skip(reason=GOLDEN_PENDING + " + harga jual belum ada di Excel")
def test_shortage_cost_satu_sku():
    """Shortage cost = qty tak terpenuhi × harga jual untuk 1 SKU."""


@pytest.mark.skip(reason=GOLDEN_PENDING + " + nilai persediaan rata-rata butuh harga material")
def test_saran_i_persen_dari_template_thesis():
    """Saran i (%) = biaya simpan tahunan ÷ nilai persediaan rata-rata × 100."""
