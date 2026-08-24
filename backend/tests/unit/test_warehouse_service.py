"""
Fase 6 v3.0, redesain 24 Agustus 2026 — kapasitas gudang per PRODUK, angka bebas.
Angka diverifikasi manual (AGENTS.md §3).
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.warehouse_service import WarehouseService, validate_capacity
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    ProductNotFoundError,
    WarehouseConfigExistsError,
    WarehouseConfigNotFoundError,
)

USER = "u1"
OTHER = "u2"


def _config(cid="c1", pid="p1", capacity=100):
    return SimpleNamespace(id=cid, product_id=pid, capacity_qty=Decimal(capacity))


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
    def __init__(self, products=None):
        self._by_id = {p: p for p in (products or [])}

    async def get_by_id(self, pid):
        return pid if pid in self._by_id else None


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
async def test_create_config():
    svc = _service()
    config = await svc.create_config("p1", 500)
    assert float(config.capacity_qty) == 500
    assert str(config.product_id) == "p1"


@pytest.mark.asyncio
async def test_create_config_produk_tidak_ada_404():
    svc = _service(products=[])
    with pytest.raises(ProductNotFoundError):
        await svc.create_config("ghost", 500)


@pytest.mark.asyncio
async def test_create_config_duplikat_409():
    svc = _service(configs=[_config(pid="p1")])
    with pytest.raises(WarehouseConfigExistsError):
        await svc.create_config("p1", 500)


@pytest.mark.asyncio
async def test_update_config():
    svc = _service(configs=[_config(cid="c1", pid="p1", capacity=100)])
    updated = await svc.update_config("c1", 250)
    assert float(updated.capacity_qty) == 250


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
