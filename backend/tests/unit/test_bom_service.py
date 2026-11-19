"""Fase 2 v3.0 — unit test BomService (CRUD + import + validasi FK)."""
from decimal import Decimal

import pytest

from app.schemas.bom import BomBulkCreate, BomCreate, BomUpdate
from app.services.bom_service import BomService, compute_line_cost
from app.utils.exceptions import (
    BomNotFoundError,
    MaterialNotFoundError,
    ProductNotFoundError,
    UploadInvalidFormatError,
)
from tests.unit.test_material_service import FakeMaterial, FakeMaterialRepository
from tests.unit.test_product_service import FakeProduct, FakeProductRepository


class FakeBom:
    def __init__(self, **kw):
        self.id = kw.get("id", "b-1")
        self.product_id = kw["product_id"]
        self.material_id = kw["material_id"]
        self.qty_per_unit = kw.get("qty_per_unit", Decimal(1))


class FakeBomRepository:
    def __init__(self, boms=None):
        self._items = {b.id: b for b in (boms or [])}
        self._seq = 0

    async def list(self, product_id=None):
        items = list(self._items.values())
        if product_id is not None:
            items = [b for b in items if str(b.product_id) == str(product_id)]
        return items

    async def get_by_id(self, bom_id):
        return self._items.get(bom_id)

    async def add(self, bom):
        self._seq += 1
        bom.id = bom.id or f"b-{self._seq}"
        self._items[bom.id] = bom
        return bom

    async def save(self, bom):
        self._items[bom.id] = bom
        return bom

    async def delete(self, bom):
        self._items.pop(bom.id, None)


def _service(boms=None, products=None, materials=None):
    return BomService(
        repo=FakeBomRepository(boms),
        products=FakeProductRepository(products or [FakeProduct(id="p1", code="P1", name="P", unit="PCS")]),
        materials=FakeMaterialRepository(materials or [FakeMaterial(id="m1", code="M1", name="M", unit="kg")]),
        model_factory=FakeBom,
    )


@pytest.mark.asyncio
async def test_create_bom():
    svc = _service()
    bom = await svc.create(BomCreate(product_id="p1", material_id="m1", qty_per_unit=Decimal("2.5")))
    assert bom.product_id == "p1"
    assert bom.qty_per_unit == Decimal("2.5")


@pytest.mark.asyncio
async def test_create_produk_tak_ada_404():
    svc = _service()
    with pytest.raises(ProductNotFoundError):
        await svc.create(BomCreate(product_id="nope", material_id="m1", qty_per_unit=Decimal(1)))


@pytest.mark.asyncio
async def test_create_material_tak_ada_404():
    svc = _service()
    with pytest.raises(MaterialNotFoundError):
        await svc.create(BomCreate(product_id="p1", material_id="nope", qty_per_unit=Decimal(1)))


@pytest.mark.asyncio
async def test_get_bom_tak_ada_404():
    svc = _service()
    with pytest.raises(BomNotFoundError):
        await svc.get("nope")


@pytest.mark.asyncio
async def test_list_filter_product_id():
    boms = [
        FakeBom(id="b1", product_id="p1", material_id="m1"),
        FakeBom(id="b2", product_id="p2", material_id="m1"),
    ]
    svc = _service(boms=boms, products=[FakeProduct(id="p1", code="P1", name="P", unit="PCS")])
    only_p1 = await svc.list(product_id="p1")
    assert {b.id for b in only_p1} == {"b1"}


@pytest.mark.asyncio
async def test_update_ganti_material_validasi():
    svc = _service(boms=[FakeBom(id="b1", product_id="p1", material_id="m1")])
    with pytest.raises(MaterialNotFoundError):
        await svc.update("b1", BomUpdate(material_id="nope"))


@pytest.mark.asyncio
async def test_import_csv_resolve_kode():
    svc = _service()
    csv = b"product_code,material_code,qty_per_unit\nP1,M1,3\n"
    result = await svc.import_csv(csv)
    assert result["imported"] == 1


@pytest.mark.asyncio
async def test_import_produk_belum_terdaftar():
    svc = _service()
    csv = b"product_code,material_code,qty_per_unit\nUNKNOWN,M1,3\n"
    with pytest.raises(ProductNotFoundError):
        await svc.import_csv(csv)


@pytest.mark.asyncio
async def test_import_kolom_wajib_hilang():
    svc = _service()
    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(b"product_code,material_code\nP1,M1\n")


# ── Biaya material per unit produk (Fase 10, 2 Oktober 2026) ──

def test_line_cost_qty_kali_harga():
    # 0,0125 kg gula × Rp14.500/kg = Rp181,25
    assert compute_line_cost(Decimal("0.0125"), Decimal("14500")) == Decimal("181.2500")


def test_line_cost_null_bila_material_tanpa_harga():
    assert compute_line_cost(Decimal("2"), None) is None


@pytest.mark.asyncio
async def test_material_prices_map_id_ke_harga():
    svc = _service(
        materials=[
            FakeMaterial(id="m1", code="M1", name="Gula", unit="kg", unit_price=Decimal("14500")),
            FakeMaterial(id="m2", code="M2", name="Botol", unit="pcs"),
        ]
    )
    prices = await svc.material_prices()
    assert prices == {"m1": Decimal("14500"), "m2": None}


# ── Input banyak material sekaligus (19 Nov 2026) ──


def _multi_service():
    def factory(**kw):
        bom = FakeBom(**kw)
        bom.id = None  # biarkan repo memberi id unik per baris
        return bom

    svc = _service(
        materials=[
            FakeMaterial(id="m1", code="M1", name="Cap", unit="PCS"),
            FakeMaterial(id="m2", code="M2", name="Bottle", unit="PCS"),
        ]
    )
    svc._model = factory
    return svc


@pytest.mark.asyncio
async def test_create_many_beberapa_material_satu_produk():
    svc = _multi_service()
    payload = BomBulkCreate(
        product_id="p1",
        items=[{"material_id": "m1", "qty_per_unit": 1}, {"material_id": "m2", "qty_per_unit": Decimal("2")}],
    )
    rows = await svc.create_many(payload)
    assert [(r.product_id, r.material_id, r.qty_per_unit) for r in rows] == [
        ("p1", "m1", Decimal(1)), ("p1", "m2", Decimal(2)),
    ]
    assert len(await svc.list("p1")) == 2


@pytest.mark.asyncio
async def test_create_many_satu_material_tak_ada_tidak_menyimpan_apapun():
    svc = _multi_service()
    payload = BomBulkCreate(
        product_id="p1",
        items=[{"material_id": "m1", "qty_per_unit": 1}, {"material_id": "ghost", "qty_per_unit": 1}],
    )
    with pytest.raises(MaterialNotFoundError):
        await svc.create_many(payload)
    assert await svc.list("p1") == []


@pytest.mark.asyncio
async def test_create_many_produk_tak_ada_404():
    svc = _multi_service()
    with pytest.raises(ProductNotFoundError):
        await svc.create_many(BomBulkCreate(product_id="nope", items=[{"material_id": "m1", "qty_per_unit": 1}]))


def test_bulk_schema_menolak_material_ganda_dan_daftar_kosong():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        BomBulkCreate(product_id="p1", items=[])
    with pytest.raises(ValidationError):
        BomBulkCreate(
            product_id="p1",
            items=[{"material_id": "m1", "qty_per_unit": 1}, {"material_id": "m1", "qty_per_unit": 2}],
        )
