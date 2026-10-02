"""
Fase 10 (2 Oktober 2026) — master template biaya: depresiasi aset penyimpanan,
overhead, saran H, CRUD + aktivasi. Angka diverifikasi manual (AGENTS.md §3).

Contoh manual (dipakai beberapa test):
  Rak      : (50.000.000 − 5.000.000) ÷ 60 bln × 10   = 7.500.000
  Pallet   : (300.000 − 0) ÷ 36 bln × 200             = 1.666.666,6667
  Forklift : (250.000.000 − 25.000.000) ÷ 96 bln × 1  = 2.343.750
  Σ depresiasi                                         = 11.510.416,6667
  Overhead : listrik 3.000.000 + keamanan 1.000.000    = 4.000.000
  Total per bulan                                      = 15.510.416,6667
  Kapasitas gudang 20.000 dus → saran H = 775,5208 / dus / bulan
"""
from decimal import Decimal
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas.cost_template import CostTemplateCreate, CostTemplateItemIn
from app.services.cost_template_service import (
    CostTemplateService,
    item_monthly_cost,
    monthly_depreciation,
    resolve_cost_params,
    summarize_template,
)
from app.utils.exceptions import CostTemplateNameExistsError, CostTemplateNotFoundError


def _asset(name, price, salvage, life, qty):
    return SimpleNamespace(
        item_type="STORAGE_ASSET",
        name=name,
        monthly_amount=None,
        purchase_price=Decimal(price),
        salvage_value=Decimal(salvage),
        useful_life_months=life,
        qty=Decimal(qty),
    )


def _overhead(name, amount):
    return SimpleNamespace(
        item_type="OVERHEAD",
        name=name,
        monthly_amount=Decimal(amount),
        purchase_price=None,
        salvage_value=None,
        useful_life_months=None,
        qty=Decimal(1),
    )


ITEMS = [
    _asset("Rak", "50000000", "5000000", 60, "10"),
    _asset("Pallet", "300000", "0", 36, "200"),
    _asset("Forklift", "250000000", "25000000", 96, "1"),
    _overhead("Listrik", "3000000"),
    _overhead("Keamanan", "1000000"),
]


# ── Fungsi murni ──


def test_depresiasi_garis_lurus_per_bulan():
    assert monthly_depreciation(Decimal("50000000"), Decimal("5000000"), 60, Decimal(10)) == Decimal(
        "7500000.0000"
    )


def test_depresiasi_dibulatkan_4_desimal():
    assert monthly_depreciation(Decimal("300000"), Decimal(0), 36, Decimal(200)) == Decimal("1666666.6667")


def test_depresiasi_nilai_sisa_kosong_dianggap_nol():
    assert monthly_depreciation(Decimal("1200"), None, 12, Decimal(1)) == Decimal("100.0000")


def test_item_monthly_cost_overhead_dikali_qty():
    item = _overhead("Listrik", "3000000")
    item.qty = Decimal(2)
    assert item_monthly_cost(item) == Decimal("6000000.0000")


def test_item_monthly_cost_aset():
    assert item_monthly_cost(ITEMS[2]) == Decimal("2343750.0000")


def test_summarize_template_saran_h():
    s = summarize_template(ITEMS, total_capacity_dus=20000)
    assert s.total_depreciation_monthly == Decimal("11510416.6667")
    assert s.total_overhead_monthly == Decimal("4000000.0000")
    assert s.total_monthly == Decimal("15510416.6667")
    assert s.suggested_holding_cost == Decimal("775.5208")


def test_summarize_template_tanpa_kapasitas_saran_h_null():
    s = summarize_template(ITEMS, total_capacity_dus=0)
    assert s.total_monthly == Decimal("15510416.6667")
    assert s.suggested_holding_cost is None


def test_summarize_template_tanpa_item():
    s = summarize_template([], total_capacity_dus=100)
    assert s.total_monthly == Decimal("0.0000")
    assert s.suggested_holding_cost == Decimal("0.0000")


# ── Validasi schema item ──


def test_item_overhead_wajib_monthly_amount():
    with pytest.raises(ValidationError):
        CostTemplateItemIn(item_type="OVERHEAD", name="Listrik")


@pytest.mark.parametrize(
    "kw",
    [
        {},  # purchase_price & umur wajib
        {"purchase_price": 1000},  # umur wajib
        {"purchase_price": 1000, "useful_life_months": 0},  # umur > 0
        {"purchase_price": 1000, "useful_life_months": 12, "salvage_value": 2000},  # sisa ≤ harga
        {"purchase_price": -1, "useful_life_months": 12},
    ],
)
def test_item_aset_tidak_valid(kw):
    with pytest.raises(ValidationError):
        CostTemplateItemIn(item_type="STORAGE_ASSET", name="Rak", **kw)


def test_item_tipe_tak_dikenal_ditolak():
    with pytest.raises(ValidationError):
        CostTemplateItemIn(item_type="PEMBELIAN", name="X", monthly_amount=1)


def test_template_biaya_negatif_ditolak():
    with pytest.raises(ValidationError):
        CostTemplateCreate(name="T", ordering_cost=-1, holding_cost=0)


# ── Orkestrasi ──


class FakeTemplate(SimpleNamespace):
    pass


class FakeTemplateRepo:
    def __init__(self, templates=None):
        self._rows = {t.id: t for t in (templates or [])}
        self._seq = 0

    async def list(self):
        return sorted(self._rows.values(), key=lambda t: t.name)

    async def get_by_id(self, template_id):
        return self._rows.get(template_id)

    async def get_by_name(self, name):
        return next((t for t in self._rows.values() if t.name == name), None)

    async def get_active(self):
        return next((t for t in self._rows.values() if t.is_active), None)

    async def add(self, template):
        self._seq += 1
        template.id = getattr(template, "id", None) or f"t{self._seq}"
        self._rows[template.id] = template
        return template

    async def save(self, template):
        return template

    async def set_active(self, template_id):
        for t in self._rows.values():
            t.is_active = t.id == template_id

    async def delete(self, template):
        self._rows.pop(template.id, None)


class FakeWarehouseConfigRepo:
    def __init__(self, configs=None):
        self._configs = configs or []

    async def list(self):
        return self._configs


def _tpl(tid="t1", name="Template 2026", active=False, items=None):
    return FakeTemplate(
        id=tid,
        name=name,
        description=None,
        ordering_cost=Decimal("250000"),
        holding_cost=Decimal("800"),
        is_active=active,
        items=list(items or []),
    )


def _template_factory(**kw):
    return FakeTemplate(id=None, is_active=False, **kw)


def _item_factory(**kw):
    return SimpleNamespace(**kw)


def _service(templates=None, configs=None):
    return CostTemplateService(
        repo=FakeTemplateRepo(templates),
        warehouse_configs=FakeWarehouseConfigRepo(configs),
        template_factory=_template_factory,
        item_factory=_item_factory,
    )


def _payload(name="Template 2026", items=None):
    return CostTemplateCreate(
        name=name,
        ordering_cost=Decimal("250000"),
        holding_cost=Decimal("800"),
        items=items
        if items is not None
        else [
            CostTemplateItemIn(item_type="OVERHEAD", name="Listrik", monthly_amount=Decimal("3000000")),
            CostTemplateItemIn(
                item_type="STORAGE_ASSET",
                name="Rak",
                purchase_price=Decimal("50000000"),
                salvage_value=Decimal("5000000"),
                useful_life_months=60,
                qty=Decimal(10),
            ),
        ],
    )


@pytest.mark.asyncio
async def test_create_template_dengan_item_tidak_otomatis_aktif():
    svc = _service()
    t = await svc.create(_payload())
    assert t.name == "Template 2026"
    assert t.is_active is False  # aktivasi selalu eksplisit
    assert [i.name for i in t.items] == ["Listrik", "Rak"]
    assert t.items[1].salvage_value == Decimal("5000000")


@pytest.mark.asyncio
async def test_create_nama_duplikat_409():
    svc = _service([_tpl(name="Template 2026")])
    with pytest.raises(CostTemplateNameExistsError):
        await svc.create(_payload(name="Template 2026"))


@pytest.mark.asyncio
async def test_get_tidak_ada_404():
    with pytest.raises(CostTemplateNotFoundError):
        await _service().get("ghost")


@pytest.mark.asyncio
async def test_update_mengganti_seluruh_item():
    svc = _service([_tpl(items=[_overhead("Lama", "1")])])
    t = await svc.update(
        "t1",
        _payload(
            name="Template 2026 rev",
            items=[CostTemplateItemIn(item_type="OVERHEAD", name="Air", monthly_amount=Decimal("500000"))],
        ),
    )
    assert t.name == "Template 2026 rev"
    assert [i.name for i in t.items] == ["Air"]


@pytest.mark.asyncio
async def test_update_ke_nama_template_lain_409():
    svc = _service([_tpl("t1", "A"), _tpl("t2", "B")])
    with pytest.raises(CostTemplateNameExistsError):
        await svc.update("t1", _payload(name="B"))


@pytest.mark.asyncio
async def test_update_nama_sama_dengan_dirinya_boleh():
    svc = _service([_tpl("t1", "A")])
    t = await svc.update("t1", _payload(name="A"))
    assert t.name == "A"


@pytest.mark.asyncio
async def test_update_tidak_ada_404():
    with pytest.raises(CostTemplateNotFoundError):
        await _service().update("ghost", _payload())


@pytest.mark.asyncio
async def test_activate_hanya_satu_aktif():
    svc = _service([_tpl("t1", "A", active=True), _tpl("t2", "B")])
    t = await svc.activate("t2")
    assert t.is_active is True
    assert (await svc.get("t1")).is_active is False
    assert (await svc.get_active()).id == "t2"


@pytest.mark.asyncio
async def test_activate_tidak_ada_404():
    with pytest.raises(CostTemplateNotFoundError):
        await _service().activate("ghost")


@pytest.mark.asyncio
async def test_get_active_belum_ada_404():
    with pytest.raises(CostTemplateNotFoundError):
        await _service([_tpl()]).get_active()


@pytest.mark.asyncio
async def test_find_active_none_bila_belum_ada():
    assert await _service([_tpl()]).find_active() is None


@pytest.mark.asyncio
async def test_delete_template_aktif_boleh():
    svc = _service([_tpl(active=True)])
    await svc.delete("t1")
    assert await svc.find_active() is None


@pytest.mark.asyncio
async def test_summary_pakai_total_kapasitas_dus_gudang():
    # 2 baris kapasitas: 200 pallet × 60 + 0 dus = 12.000 dus; 8.000 dus → 20.000 dus
    configs = [
        SimpleNamespace(capacity_mode="PALLET", pallet_qty=200, dus_qty=0, dus_per_pallet=60),
        SimpleNamespace(capacity_mode="DUS", pallet_qty=0, dus_qty=8000, dus_per_pallet=None),
    ]
    svc = _service([_tpl(items=ITEMS)], configs=configs)
    s = await svc.summary("t1")
    assert s.total_capacity_dus == Decimal("20000.0000")
    assert s.suggested_holding_cost == Decimal("775.5208")


@pytest.mark.asyncio
async def test_summary_tanpa_kapasitas_gudang_saran_h_null():
    s = await _service([_tpl(items=ITEMS)]).summary("t1")
    assert s.total_capacity_dus == Decimal("0.0000")
    assert s.suggested_holding_cost is None


# ── Sumber S & H untuk EOQ/TIC (Fase 10.6) ──


def test_resolve_cost_params_pakai_template_aktif():
    settings = SimpleNamespace(DEFAULT_ORDERING_COST=1.0, DEFAULT_HOLDING_COST_RATE=2.0)
    p = resolve_cost_params(_tpl(active=True), settings)
    assert (p.ordering_cost, p.holding_cost) == (250000.0, 800.0)
    assert p.source == "template"
    assert p.template_name == "Template 2026"


def test_resolve_cost_params_fallback_env_tanpa_template():
    settings = SimpleNamespace(DEFAULT_ORDERING_COST=1.0, DEFAULT_HOLDING_COST_RATE=2.0)
    p = resolve_cost_params(None, settings)
    assert (p.ordering_cost, p.holding_cost, p.source, p.template_name) == (1.0, 2.0, "env", None)
