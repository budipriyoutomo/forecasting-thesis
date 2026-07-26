"""
Fase 6 v3.0 — kapasitas gudang. Angka diverifikasi manual (AGENTS.md §3).
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.services.warehouse_service import (
    WarehouseService,
    compute_material_capacity,
    compute_pallet_capacity,
    validate_capacity,
)
from app.utils.exceptions import (
    ForbiddenRoleError,
    ForecastRunNotFoundError,
    WarehouseConfigNotFoundError,
)

USER = "u1"
OTHER = "u2"


def _rec(mid, ss=0, buffer=0, eoq=0):
    return SimpleNamespace(
        material_id=mid, safety_stock=Decimal(ss), buffer_stock=Decimal(buffer), eoq_qty=Decimal(eoq)
    )


def _material(mid, qpp):
    return SimpleNamespace(id=mid, qty_per_pallet=Decimal(qpp) if qpp is not None else None)


# ── Fungsi murni ──


def test_pallet_capacity_footprint():
    # area 100 m², palet 2×1.25 → footprint 2.5 → 40 palet
    assert compute_pallet_capacity(100, {"length": 2, "width": 1.25, "height": 1}) == 40


def test_pallet_capacity_footprint_nol_aman():
    assert compute_pallet_capacity(100, {"length": 0, "width": 1, "height": 1}) == 0


def test_material_capacity():
    assert compute_material_capacity(40, 500) == pytest.approx(20000)


def test_validate_capacity_muat():
    # kapasitas 100 palet ; M1 butuh 500/250=2 palet, M2 250/250=1 → total 3 ≤ 100
    recs = [_rec("M1", ss=100, eoq=400), _rec("M2", ss=250)]
    materials = {"M1": _material("M1", 250), "M2": _material("M2", 250)}
    res = validate_capacity(recs, materials, 100, {"length": 1, "width": 1, "height": 1})
    assert res.total_pallet_capacity == 100
    assert res.total_pallet_required == pytest.approx(3)
    assert res.is_within_capacity is True


def test_validate_capacity_melebihi():
    recs = [_rec("M1", ss=100, eoq=400), _rec("M2", ss=250)]
    materials = {"M1": _material("M1", 250), "M2": _material("M2", 250)}
    res = validate_capacity(recs, materials, 1, {"length": 1, "width": 1, "height": 1})
    assert res.total_pallet_capacity == 1
    assert res.is_within_capacity is False


def test_validate_capacity_material_tanpa_qpp_dilewati():
    recs = [_rec("M1", ss=500)]
    materials = {"M1": _material("M1", None)}
    res = validate_capacity(recs, materials, 100, {"length": 1, "width": 1, "height": 1})
    assert res.total_pallet_required == 0.0
    assert res.is_within_capacity is True


# ── Orkestrasi ──


class FakeConfigRepo:
    def __init__(self, configs=None):
        self._by_cat = {c.category: c for c in (configs or [])}

    async def get_by_category(self, category):
        return self._by_cat.get(category)

    async def add(self, config):
        self._by_cat[config.category] = config
        return config

    async def save(self, config):
        self._by_cat[config.category] = config
        return config


class FakeValidationRepo:
    def __init__(self):
        self.by_run = {}

    async def replace_for_run(self, run_id, validation):
        self.by_run[str(run_id)] = validation
        return validation


class FakeReorderRepo:
    def __init__(self, recs):
        self._recs = recs

    async def list_by_run(self, run_id):
        return self._recs


class FakeMaterialRepo:
    def __init__(self, materials):
        self._by_id = {str(m.id): m for m in materials}

    async def get_by_id(self, mid):
        return self._by_id.get(str(mid))


class FakeForecastRepo:
    def __init__(self, run):
        self._run = run

    async def get_run(self, run_id):
        return self._run if self._run and str(self._run.id) == str(run_id) else None


def _config(cat="packaging", area=100, dim=None):
    return SimpleNamespace(category=cat, warehouse_area_m2=Decimal(area), pallet_dimension=dim or {"length": 1, "width": 1, "height": 1})


def _service(run=None, recs=None, materials=None, configs=None):
    return WarehouseService(
        config_repo=FakeConfigRepo(configs),
        validation_repo=FakeValidationRepo(),
        reorder_repo=FakeReorderRepo(recs or []),
        materials=FakeMaterialRepo(materials or []),
        forecast_repo=FakeForecastRepo(run),
    )


@pytest.mark.asyncio
async def test_get_config_belum_ada_404():
    svc = _service()
    with pytest.raises(WarehouseConfigNotFoundError):
        await svc.get_config()


@pytest.mark.asyncio
async def test_upsert_config_create_lalu_update():
    svc = _service()
    c1 = await svc.upsert_config("packaging", 100, {"length": 1, "width": 1, "height": 1})
    assert float(c1.warehouse_area_m2) == 100
    c2 = await svc.upsert_config("packaging", 250, {"length": 1, "width": 1, "height": 1})
    assert float(c2.warehouse_area_m2) == 250


@pytest.mark.asyncio
async def test_validate_for_run_persist_flag():
    run = SimpleNamespace(id="r1", user_id=USER)
    svc = _service(
        run=run,
        recs=[_rec("M1", ss=100, eoq=400)],
        materials=[_material("M1", 250)],
        configs=[_config(area=100)],
    )
    v = await svc.validate_for_run(USER, "r1")
    assert v.is_within_capacity is True
    assert float(v.total_pallet_required) == pytest.approx(2)


@pytest.mark.asyncio
async def test_validate_for_run_tanpa_config_404():
    run = SimpleNamespace(id="r1", user_id=USER)
    svc = _service(run=run, recs=[], materials=[])
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
