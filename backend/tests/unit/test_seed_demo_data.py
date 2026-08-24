"""
Unit test seeding data demo (app/scripts/seed_demo_data.py).

Repository di-fake (in-memory) — pola sama seperti tests/unit/test_seed_dev_users.py.
Data demand 2024 diambil dari `Simulasi Thesis.xlsx` sheet "Bab I Plan vs Forecast";
tahun lain diturunkan secara deterministik supaya histori cukup panjang untuk LSTM.
"""
from datetime import date

import pytest

from app.config import get_settings
from app.scripts.seed_demo_data import (
    DEMAND_2024,
    DEMO_BOM,
    DEMO_MATERIALS,
    DEMO_PRODUCTS,
    DEMO_WAREHOUSE_CAPACITY,
    build_demand_series,
    seed_demo_data,
)


class FakeCodeRepository:
    """Fake untuk product/material repository (get_by_code + add)."""

    def __init__(self):
        self.items = []
        self._by_code = {}

    async def get_by_code(self, code):
        return self._by_code.get(code)

    async def add(self, item):
        item.id = f"id-{item.code}"
        self.items.append(item)
        self._by_code[item.code] = item
        return item


class FakeBomRepository:
    def __init__(self):
        self.items = []

    async def list(self, product_id=None):
        return [b for b in self.items if product_id is None or str(b.product_id) == str(product_id)]

    async def add(self, bom):
        self.items.append(bom)
        return bom


class FakeDemandRepository:
    def __init__(self):
        self.rows = []

    async def bulk_add(self, rows):
        self.rows.extend(rows)
        return len(rows)

    async def list_for_product(self, product_id, product_code):
        return [
            r
            for r in self.rows
            if str(r.product_id) == str(product_id) or r.product_code == product_code
        ]


class FakeWarehouseRepository:
    def __init__(self):
        self.configs_by_product = {}

    async def get_by_product(self, product_id):
        return self.configs_by_product.get(product_id)

    async def add(self, config):
        self.configs_by_product[config.product_id] = config
        return config


class FakeUploadRepository:
    def __init__(self):
        self.items = []

    async def add(self, upload):
        upload.id = f"upload-{len(self.items)}"
        self.items.append(upload)
        return upload


def make_repos():
    return {
        "products": FakeCodeRepository(),
        "materials": FakeCodeRepository(),
        "boms": FakeBomRepository(),
        "demand": FakeDemandRepository(),
        "warehouse": FakeWarehouseRepository(),
        "uploads": FakeUploadRepository(),
    }


# ── Konsistensi konstanta ────────────────────────────────────────────────


def test_setiap_produk_demo_punya_data_demand_2024():
    assert {p.code for p in DEMO_PRODUCTS} == set(DEMAND_2024)


def test_bom_hanya_merujuk_produk_dan_material_yang_ada():
    product_codes = {p.code for p in DEMO_PRODUCTS}
    material_codes = {m.code for m in DEMO_MATERIALS}
    for line in DEMO_BOM:
        assert line.product_code in product_codes
        assert line.material_code in material_codes
        assert float(line.qty_per_unit) > 0


def test_setiap_produk_punya_minimal_satu_baris_bom():
    # Tanpa BOM, breakdown material & reorder tidak menghasilkan apa pun (BOM_NOT_FOUND).
    assert {line.product_code for line in DEMO_BOM} == {p.code for p in DEMO_PRODUCTS}


def test_material_dimensi_fisik_valid():
    for material in DEMO_MATERIALS:
        assert set(material.dimension) == {"length", "width", "height"}


def test_kapasitas_gudang_per_produk_valid():
    product_codes = {p.code for p in DEMO_PRODUCTS}
    assert {c.product_code for c in DEMO_WAREHOUSE_CAPACITY} == product_codes
    for c in DEMO_WAREHOUSE_CAPACITY:
        assert c.capacity_qty > 0


# ── Deret demand ─────────────────────────────────────────────────────────


def test_deret_demand_cukup_panjang_untuk_semua_engine_termasuk_lstm():
    settings = get_settings()
    for code in DEMAND_2024:
        series = build_demand_series(code)
        assert len(series) >= settings.LSTM_MIN_PERIODS


def test_deret_demand_bulanan_terurut_dan_tanpa_periode_ganda():
    series = build_demand_series("KBYPL 200")
    periods = [point.period for point in series]
    assert periods == sorted(periods)
    assert len(set(periods)) == len(periods)
    assert all(p.day == 1 for p in periods)
    assert periods[0] == date(2023, 1, 1)
    # Histori berhenti Juni 2026 → forecast run meramal periode yang belum terjadi.
    assert periods[-1] == date(2026, 6, 1)


def test_deret_demand_memakai_angka_riil_2024_apa_adanya():
    series = build_demand_series("KBYPL 200")
    real_2024 = DEMAND_2024["KBYPL 200"]
    points_2024 = [p for p in series if p.period.year == 2024]

    assert len(points_2024) == 12
    for point, (forecast_existing, planning, actual) in zip(points_2024, real_2024):
        assert point.forecast_existing == forecast_existing
        assert point.planning == planning
        assert point.actual == actual


def test_deret_demand_deterministik():
    assert build_demand_series("KBYST 200") == build_demand_series("KBYST 200")


def test_bulan_tanpa_permintaan_tetap_nol_di_tahun_turunan():
    # KBYSR 200 Januari 2024 = 0 → turunannya tidak boleh mengarang angka.
    series = build_demand_series("KBYSR 200")
    januari = [p for p in series if p.period.month == 1]
    assert all(p.actual == 0 for p in januari)


def test_actual_tidak_pernah_none():
    # Kolom `actual` NOT NULL di demand_history.
    for code in DEMAND_2024:
        assert all(point.actual is not None for point in build_demand_series(code))


# ── Seeding ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_seed_membuat_seluruh_master_data_dan_histori():
    repos = make_repos()

    summary = await seed_demo_data(user_id="user-1", **repos)

    assert summary.products_created == len(DEMO_PRODUCTS)
    assert summary.materials_created == len(DEMO_MATERIALS)
    assert summary.boms_created == len(DEMO_BOM)
    assert summary.warehouse_created == len(DEMO_WAREHOUSE_CAPACITY)
    assert summary.demand_rows == sum(len(build_demand_series(p.code)) for p in DEMO_PRODUCTS)
    assert len(repos["demand"].rows) == summary.demand_rows
    product = await repos["products"].get_by_code("KBYPL 200")
    assert repos["warehouse"].configs_by_product[product.id] is not None


@pytest.mark.asyncio
async def test_seed_menautkan_histori_ke_upload_session_dan_produk():
    repos = make_repos()

    await seed_demo_data(user_id="user-1", **repos)

    # demand_history.upload_session_id NOT NULL → sesi upload sintetis wajib ada.
    assert len(repos["uploads"].items) == 1
    upload_id = repos["uploads"].items[0].id
    assert all(row.upload_session_id == upload_id for row in repos["demand"].rows)

    product = await repos["products"].get_by_code("KBYPL 200")
    rows = await repos["demand"].list_for_product(product.id, product.code)
    assert len(rows) == len(build_demand_series("KBYPL 200"))
    assert all(row.product_id == product.id for row in rows)


@pytest.mark.asyncio
async def test_seed_idempoten_dijalankan_dua_kali_tidak_menduplikasi():
    repos = make_repos()

    await seed_demo_data(user_id="user-1", **repos)
    summary = await seed_demo_data(user_id="user-1", **repos)

    assert summary.products_created == 0
    assert summary.materials_created == 0
    assert summary.boms_created == 0
    assert summary.demand_rows == 0
    assert summary.warehouse_created == 0
    assert len(repos["uploads"].items) == 1  # tidak bikin sesi upload kosong
    assert len(repos["demand"].rows) == sum(
        len(build_demand_series(p.code)) for p in DEMO_PRODUCTS
    )
