"""
Fase 11.3 — BOM multi-level (REVISI_V2 §3.4, Keputusan #4).

Level 0 FG → level 1 (Cap, Bottle) via `boms`; level 2 (Preform ← Bottle) via
`material_components` (material → material). Bottle dibeli jadi → komponen level 2
hanya INFORMASI (tidak masuk EOQ/kapasitas). Siklus (A→B→A) → BOM_CYCLE_DETECTED.
"""
from types import SimpleNamespace

import pytest

from app.services.material_component_service import (
    MaterialComponentService,
    build_bom_tree,
    would_create_cycle,
)
from app.utils.exceptions import (
    BomCycleDetectedError,
    MaterialComponentNotFoundError,
    MaterialNotFoundError,
    ProductNotFoundError,
)


def test_would_create_cycle():
    edges = {"btl": {"pre"}, "pre": {"resin"}}
    assert would_create_cycle(edges, "resin", "btl") is True  # resin → btl → pre → resin
    assert would_create_cycle(edges, "btl", "btl") is True  # diri sendiri
    assert would_create_cycle(edges, "cap", "pre") is False


M = {
    "cap": SimpleNamespace(id="cap", code="CAP-WHITE", name="Cap White", unit="PCS"),
    "btl": SimpleNamespace(id="btl", code="BTL-WHITE", name="Bottle White", unit="PCS"),
    "pre": SimpleNamespace(id="pre", code="PRE-WHITE", name="Preform White", unit="PCS"),
}


def test_build_bom_tree_tiga_level():
    product = SimpleNamespace(id="p1", code="KBYPL 200", name="Original")
    boms = [SimpleNamespace(material_id="cap", qty_per_unit=1), SimpleNamespace(material_id="btl", qty_per_unit=1)]
    comps = {"btl": [SimpleNamespace(id="c1", component_material_id="pre", qty_per_unit=1)]}

    tree = build_bom_tree(product, boms, M, comps)

    assert tree["level"] == 0 and tree["code"] == "KBYPL 200"
    level1 = {n["code"]: n for n in tree["children"]}
    assert set(level1) == {"CAP-WHITE", "BTL-WHITE"}
    assert level1["BTL-WHITE"]["level"] == 1 and level1["BTL-WHITE"]["purchased"] is True
    pre = level1["BTL-WHITE"]["children"][0]
    assert pre["code"] == "PRE-WHITE" and pre["level"] == 2
    assert pre["purchased"] is False  # informasi saja, tidak dipesan
    assert pre["component_id"] == "c1"


class FakeCompRepo:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def list(self, parent_id=None):
        return [r for r in self.rows if parent_id is None or str(r.parent_material_id) == str(parent_id)]

    async def get_by_id(self, cid):
        return next((r for r in self.rows if str(r.id) == str(cid)), None)

    async def add(self, row):
        row.id = row.id or f"c{len(self.rows) + 1}"
        self.rows.append(row)
        return row

    async def delete(self, row):
        self.rows.remove(row)


class Repo:
    def __init__(self, items):
        self._by = {str(i.id): i for i in items}

    async def get_by_id(self, i):
        return self._by.get(str(i))

    async def list(self):
        return list(self._by.values())


class FakeBoms:
    def __init__(self, lines):
        self._lines = lines

    async def list(self, product_id=None):
        return [b for b in self._lines if product_id is None or str(b.product_id) == str(product_id)]


def _svc(rows=None):
    repo = FakeCompRepo(rows)
    products = Repo([SimpleNamespace(id="p1", code="KBYPL 200", name="Original")])
    boms = FakeBoms([SimpleNamespace(product_id="p1", material_id="btl", qty_per_unit=1)])
    svc = MaterialComponentService(repo, Repo(M.values()), products, boms, factory=lambda **kw: SimpleNamespace(id=None, **kw))
    return svc, repo


@pytest.mark.asyncio
async def test_add_list_delete_komponen():
    svc, repo = _svc()
    row = await svc.add("btl", "pre", 1)
    assert row.parent_material_id == "btl" and row.component_material_id == "pre"
    assert len(await svc.list("btl")) == 1

    await svc.delete(row.id)
    assert repo.rows == []
    with pytest.raises(MaterialComponentNotFoundError):
        await svc.delete("nope")


@pytest.mark.asyncio
async def test_add_siklus_ditolak():
    svc, repo = _svc([SimpleNamespace(id="c1", parent_material_id="btl", component_material_id="pre", qty_per_unit=1)])
    with pytest.raises(BomCycleDetectedError):
        await svc.add("pre", "btl", 1)
    with pytest.raises(BomCycleDetectedError):
        await svc.add("cap", "cap", 1)
    assert len(repo.rows) == 1


@pytest.mark.asyncio
async def test_add_material_tidak_ada_404():
    svc, _ = _svc()
    with pytest.raises(MaterialNotFoundError):
        await svc.add("btl", "zzz", 1)


@pytest.mark.asyncio
async def test_tree_produk():
    svc, _ = _svc([SimpleNamespace(id="c1", parent_material_id="btl", component_material_id="pre", qty_per_unit=1)])
    tree = await svc.tree("p1")
    assert tree["children"][0]["children"][0]["code"] == "PRE-WHITE"
    with pytest.raises(ProductNotFoundError):
        await svc.tree("nope")
