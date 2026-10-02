"""
Fase 6 v3.0, redesain 24 Agustus 2026 — kapasitas gudang per PRODUK.
Fase 10 (2 Oktober 2026) — input pallet/dus/kombinasi, `capacity_qty` turunan server.
Angka diverifikasi manual (AGENTS.md §3).
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.warehouse_service import (
    CapacityInput,
    WarehouseService,
    compute_effective_capacity,
    validate_capacity,
)
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    ProductNotFoundError,
    WarehouseCapacityInvalidError,
    WarehouseConfigExistsError,
    WarehouseConfigNotFoundError,
)

USER = "u1"
OTHER = "u2"


def _config(cid="c1", pid="p1", capacity=100, uom="DUS"):
    return SimpleNamespace(
        id=cid,
        product_id=pid,
        capacity_mode="DUS",
        pallet_qty=Decimal(0),
        dus_qty=Decimal(capacity),
        dus_per_pallet=None,
        pcs_per_dus=None,
        capacity_qty=Decimal(capacity),
        uom=uom,
    )


def _input(mode="DUS", pallet_qty=0, dus_qty=0, dus_per_pallet=None, pcs_per_dus=None):
    return CapacityInput(
        capacity_mode=mode,
        pallet_qty=pallet_qty,
        dus_qty=dus_qty,
        dus_per_pallet=dus_per_pallet,
        pcs_per_dus=pcs_per_dus,
    )


def _result(pid, status="COMPLETED", values=None):
    forecast_data = [{"date": "2026-01-01", "value": v} for v in (values or [])] if values is not None else None
    return SimpleNamespace(product_id=pid, status=status, forecast_data=forecast_data)


# ── Fungsi murni ──


def test_validate_capacity_muat():
    configs = [_config(pid="p1", capacity=100)]
    res = validate_capacity(configs, {"p1": 80})
    assert res.is_within_capacity is True
    assert res.details[0].required_qty == pytest.approx(80)
    assert res.details[0].capacity_qty == pytest.approx(100)


def test_validate_capacity_melebihi():
    configs = [_config(pid="p1", capacity=100)]
    res = validate_capacity(configs, {"p1": 150})
    assert res.is_within_capacity is False
    assert res.details[0].is_within_capacity is False


def test_validate_capacity_agregat_false_bila_salah_satu_produk_melebihi():
    configs = [_config(cid="c1", pid="p1", capacity=100), _config(cid="c2", pid="p2", capacity=50)]
    res = validate_capacity(configs, {"p1": 80, "p2": 60})
    assert res.is_within_capacity is False
    assert len(res.details) == 2


def test_validate_capacity_produk_tanpa_forecast_dilewati():
    configs = [_config(pid="p1", capacity=100)]
    res = validate_capacity(configs, {})
    assert res.details == []
    assert res.is_within_capacity is True  # tak ada yang dibandingkan → tak ada yang melebihi


# ── Kapasitas efektif pallet/dus (Fase 10) ──


def test_kapasitas_mode_dus_unit_dus():
    # 500 dus, unit produk DUS → 500 dus = 500 unit produk
    assert compute_effective_capacity(_input("DUS", dus_qty=500), "DUS") == (500, 500)


def test_kapasitas_mode_pallet_unit_karton():
    # 10 pallet × 60 dus/pallet = 600 dus; dus_qty diabaikan di mode PALLET
    res = compute_effective_capacity(_input("PALLET", pallet_qty=10, dus_qty=99, dus_per_pallet=60), "Karton")
    assert res == (600, 600)


def test_kapasitas_mode_kombinasi_unit_pcs():
    # (10 × 60) + 25 = 625 dus; × 24 pcs/dus = 15.000 pcs
    res = compute_effective_capacity(
        _input("COMBINED", pallet_qty=10, dus_qty=25, dus_per_pallet=60, pcs_per_dus=24), "PCS"
    )
    assert res == (625, 15000)


def test_kapasitas_mode_dus_abaikan_pallet():
    # mode DUS: pallet_qty & dus_per_pallet tidak ikut dihitung
    res = compute_effective_capacity(_input("DUS", pallet_qty=10, dus_qty=40, dus_per_pallet=60), "dus")
    assert res == (40, 40)


def test_kapasitas_unit_dus_like_case_insensitive_dan_spasi():
    assert compute_effective_capacity(_input("DUS", dus_qty=7), " box ") == (7, 7)
    assert compute_effective_capacity(_input("DUS", dus_qty=7), "ctn") == (7, 7)


def test_kapasitas_unit_dus_like_abaikan_pcs_per_dus():
    assert compute_effective_capacity(_input("DUS", dus_qty=10, pcs_per_dus=24), "Karton") == (10, 10)


def test_kapasitas_pecahan_tetap_presisi():
    # 2,5 pallet × 40 = 100 dus + 0,5 dus = 100,5; × 12 = 1.206 pcs
    res = compute_effective_capacity(
        _input("COMBINED", pallet_qty=2.5, dus_qty=0.5, dus_per_pallet=40, pcs_per_dus=12), "PCS"
    )
    assert res == (pytest.approx(100.5), pytest.approx(1206))


@pytest.mark.parametrize(
    "inp, unit",
    [
        (_input("PALLET", pallet_qty=10), "DUS"),  # dus_per_pallet wajib
        (_input("PALLET", pallet_qty=10, dus_per_pallet=0), "DUS"),  # dus_per_pallet > 0
        (_input("COMBINED", pallet_qty=1, dus_qty=1), "DUS"),  # dus_per_pallet wajib
        (_input("DUS", dus_qty=10), "PCS"),  # unit non-dus → pcs_per_dus wajib
        (_input("DUS", dus_qty=10, pcs_per_dus=0), "PCS"),  # pcs_per_dus > 0
        (_input("DUS", dus_qty=-1), "DUS"),  # qty negatif
        (_input("COMBINED", pallet_qty=-1, dus_qty=5, dus_per_pallet=10), "DUS"),
        (_input("DUS", dus_qty=0), "DUS"),  # kapasitas efektif 0
        (_input("PALLET", pallet_qty=0, dus_per_pallet=60), "DUS"),
        (_input("RAK", dus_qty=10), "DUS"),  # mode tak dikenal
    ],
)
def test_kapasitas_input_tidak_valid(inp, unit):
    with pytest.raises(WarehouseCapacityInvalidError):
        compute_effective_capacity(inp, unit)


# ── Orkestrasi ──


class FakeConfigRepo:
    def __init__(self, configs=None):
        self._rows = {c.id: c for c in (configs or [])}
        self._by_product = {c.product_id: c for c in (configs or [])}

    async def list(self):
        return list(self._rows.values())

    async def get_by_id(self, config_id):
        return self._rows.get(config_id)

    async def get_by_product(self, product_id):
        return self._by_product.get(product_id)

    async def add(self, config):
        self._rows[config.id] = config
        self._by_product[config.product_id] = config
        return config

    async def save(self, config):
        return config

    async def delete(self, config):
        self._rows.pop(config.id, None)
        self._by_product.pop(config.product_id, None)


class FakeValidationRepo:
    def __init__(self):
        self.by_run = {}

    async def replace_for_run(self, run_id, validation):
        self.by_run[str(run_id)] = validation
        return validation


class FakeForecastRepo:
    def __init__(self, run, results=None):
        self._run = run
        self._results = results or []

    async def get_run(self, run_id):
        return self._run if self._run and str(self._run.id) == str(run_id) else None

    async def list_results(self, run_id):
        return self._results


class FakeProductRepo:
    """`products`: list id (unit default DUS) atau dict {id: unit}."""

    def __init__(self, products=None):
        units = products if isinstance(products, dict) else {p: "DUS" for p in (products or [])}
        self._by_id = {pid: SimpleNamespace(id=pid, unit=unit) for pid, unit in units.items()}

    async def get_by_id(self, pid):
        return self._by_id.get(pid)


def _service(run=None, results=None, configs=None, products=None):
    return WarehouseService(
        config_repo=FakeConfigRepo(configs),
        validation_repo=FakeValidationRepo(),
        forecast_repo=FakeForecastRepo(run, results),
        products=FakeProductRepo(products if products is not None else ["p1", "p2"]),
    )


@pytest.mark.asyncio
async def test_get_config_belum_ada_404():
    svc = _service()
    with pytest.raises(WarehouseConfigNotFoundError):
        await svc.get_config("ghost")


@pytest.mark.asyncio
async def test_create_config_mode_dus():
    svc = _service()
    config = await svc.create_config("p1", _input("DUS", dus_qty=500))
    assert str(config.product_id) == "p1"
    assert config.capacity_mode == "DUS"
    assert float(config.capacity_qty) == 500
    assert config.uom == "DUS"  # uom turunan = products.unit


@pytest.mark.asyncio
async def test_create_config_kombinasi_unit_pcs_hitung_capacity_qty():
    svc = _service(products={"p1": "PCS"})
    config = await svc.create_config(
        "p1", _input("COMBINED", pallet_qty=10, dus_qty=25, dus_per_pallet=60, pcs_per_dus=24)
    )
    assert float(config.capacity_qty) == 15000
    assert config.uom == "PCS"
    assert float(config.pallet_qty) == 10
    assert float(config.dus_qty) == 25
    assert float(config.dus_per_pallet) == 60
    assert float(config.pcs_per_dus) == 24


@pytest.mark.asyncio
async def test_create_config_normalisasi_field_tak_relevan():
    # mode PALLET → dus_qty disimpan 0; unit dus-like → pcs_per_dus None
    svc = _service(products={"p1": "Karton"})
    config = await svc.create_config(
        "p1", _input("PALLET", pallet_qty=3, dus_qty=99, dus_per_pallet=50, pcs_per_dus=12)
    )
    assert float(config.dus_qty) == 0
    assert config.pcs_per_dus is None
    assert float(config.capacity_qty) == 150

    svc = _service(products={"p2": "DUS"})
    config = await svc.create_config("p2", _input("DUS", pallet_qty=3, dus_qty=20, dus_per_pallet=50))
    assert float(config.pallet_qty) == 0
    assert config.dus_per_pallet is None


@pytest.mark.asyncio
async def test_create_config_input_tidak_valid_400():
    svc = _service(products={"p1": "PCS"})
    with pytest.raises(WarehouseCapacityInvalidError):
        await svc.create_config("p1", _input("DUS", dus_qty=10))  # pcs_per_dus wajib


@pytest.mark.asyncio
async def test_create_config_produk_tidak_ada_404():
    svc = _service(products=[])
    with pytest.raises(ProductNotFoundError):
        await svc.create_config("ghost", _input("DUS", dus_qty=500))


@pytest.mark.asyncio
async def test_create_config_duplikat_409():
    svc = _service(configs=[_config(pid="p1")])
    with pytest.raises(WarehouseConfigExistsError):
        await svc.create_config("p1", _input("DUS", dus_qty=500))


@pytest.mark.asyncio
async def test_update_config_ganti_mode_hitung_ulang():
    svc = _service(configs=[_config(cid="c1", pid="p1", capacity=100)], products={"p1": "PCS"})
    updated = await svc.update_config(
        "c1", _input("PALLET", pallet_qty=4, dus_per_pallet=50, pcs_per_dus=6)
    )
    assert updated.capacity_mode == "PALLET"
    assert float(updated.capacity_qty) == 1200  # 4 × 50 × 6
    assert updated.uom == "PCS"


@pytest.mark.asyncio
async def test_update_config_input_tidak_valid_400():
    svc = _service(configs=[_config(cid="c1", pid="p1")])
    with pytest.raises(WarehouseCapacityInvalidError):
        await svc.update_config("c1", _input("PALLET", pallet_qty=4))


@pytest.mark.asyncio
async def test_update_config_tidak_ada_404():
    svc = _service()
    with pytest.raises(WarehouseConfigNotFoundError):
        await svc.update_config("ghost", _input("DUS", dus_qty=5))


@pytest.mark.asyncio
async def test_delete_config():
    svc = _service(configs=[_config(cid="c1", pid="p1")])
    await svc.delete_config("c1")
    with pytest.raises(WarehouseConfigNotFoundError):
        await svc.get_config("c1")


@pytest.mark.asyncio
async def test_validate_for_run_persist_flag():
    run = SimpleNamespace(id="r1", user_id=USER)
    svc = _service(
        run=run,
        results=[_result("p1", values=[40, 40])],
        configs=[_config(pid="p1", capacity=100)],
    )
    v = await svc.validate_for_run(USER, "r1")
    assert v.is_within_capacity is True
    assert v.details[0]["required_qty"] == pytest.approx(80)


@pytest.mark.asyncio
async def test_validate_for_run_produk_gagal_forecast_dilewati():
    run = SimpleNamespace(id="r1", user_id=USER)
    svc = _service(
        run=run,
        results=[_result("p1", status="INSUFFICIENT_DATA", values=None)],
        configs=[_config(pid="p1", capacity=100)],
    )
    v = await svc.validate_for_run(USER, "r1")
    assert v.details == []
    assert v.is_within_capacity is True


@pytest.mark.asyncio
async def test_validate_for_run_tanpa_config_404():
    run = SimpleNamespace(id="r1", user_id=USER)
    svc = _service(run=run, results=[])
    with pytest.raises(WarehouseConfigNotFoundError):
        await svc.validate_for_run(USER, "r1")


@pytest.mark.asyncio
async def test_validate_for_run_milik_user_lain_403():
    run = SimpleNamespace(id="r1", user_id=OTHER)
    svc = _service(run=run, configs=[_config()])
    with pytest.raises(ForbiddenRoleError):
        await svc.validate_for_run(USER, "r1")


@pytest.mark.asyncio
async def test_validate_for_run_tidak_ada_404():
    svc = _service(run=None, configs=[_config()])
    with pytest.raises(ForecastRunNotFoundError):
        await svc.validate_for_run(USER, "ghost")
