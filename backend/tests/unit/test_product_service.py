"""Fase 2 v3.0 — unit test ProductService (CRUD + import), repository di-mock."""
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.product import ProductCreate, ProductUpdate
from app.services.product_service import ProductService
from app.utils.exceptions import (
    ProductCodeExistsError,
    ProductNotFoundError,
    UploadInvalidFormatError,
)


class FakeProduct:
    def __init__(self, **kw):
        self.id = kw.get("id", "p-" + kw["code"])
        self.code = kw["code"]
        self.name = kw.get("name", "")
        self.category = kw.get("category")
        self.unit = kw.get("unit", "PCS")
        self.selling_price = kw.get("selling_price")


class FakeProductRepository:
    def __init__(self, products=None):
        self._items = {p.id: p for p in (products or [])}

    async def list(self):
        return sorted(self._items.values(), key=lambda p: p.code)

    async def get_by_id(self, product_id):
        return self._items.get(product_id)

    async def get_by_code(self, code):
        return next((p for p in self._items.values() if p.code == code), None)

    async def add(self, product):
        product.id = product.id or ("p-" + product.code)
        self._items[product.id] = product
        return product

    async def save(self, product):
        self._items[product.id] = product
        return product

    async def delete(self, product):
        self._items.pop(product.id, None)


def _service(products=None):
    return ProductService(FakeProductRepository(products), model_factory=FakeProduct)


@pytest.mark.asyncio
async def test_create_produk():
    svc = _service()
    p = await svc.create(ProductCreate(code="KBYPL 200", name="KIN Yogurt Original 200ml", unit="PCS"))
    assert p.code == "KBYPL 200"


@pytest.mark.asyncio
async def test_create_kode_duplikat_ditolak():
    svc = _service([FakeProduct(code="KBYPL 200", name="X", unit="PCS")])
    with pytest.raises(ProductCodeExistsError):
        await svc.create(ProductCreate(code="KBYPL 200", name="Y", unit="PCS"))


@pytest.mark.asyncio
async def test_get_tidak_ada_404():
    svc = _service()
    with pytest.raises(ProductNotFoundError):
        await svc.get("nope")


@pytest.mark.asyncio
async def test_update_kode_ke_yang_sudah_ada_ditolak():
    svc = _service([
        FakeProduct(id="p1", code="A", name="A", unit="PCS"),
        FakeProduct(id="p2", code="B", name="B", unit="PCS"),
    ])
    with pytest.raises(ProductCodeExistsError):
        await svc.update("p1", ProductUpdate(code="B"))


@pytest.mark.asyncio
async def test_import_csv_sukses():
    svc = _service()
    csv = b"code,name,category,unit\nKBYPL 200,KIN Yogurt 200ml,RTD Yogurt,PCS\nKBYPL 700,KIN Yogurt 700ml,RTD Yogurt,PCS\n"
    result = await svc.import_csv(csv)
    assert result["imported"] == 2


@pytest.mark.asyncio
async def test_import_kolom_wajib_hilang():
    svc = _service()
    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(b"code,name\nX,Y\n")


@pytest.mark.asyncio
async def test_import_duplikat_dalam_file():
    svc = _service()
    csv = b"code,name,unit\nDUP,A,PCS\nDUP,B,PCS\n"
    with pytest.raises(ProductCodeExistsError):
        await svc.import_csv(csv)


# ── Harga produk (Fase 10, 2 Oktober 2026) ──


@pytest.mark.asyncio
async def test_create_produk_dengan_harga_produk():
    svc = _service()
    p = await svc.create(ProductCreate(code="A", name="A", unit="PCS", selling_price=Decimal("6000")))
    assert p.selling_price == Decimal("6000")


def test_schema_produk_tanpa_hpp():
    # Satu harga saja (harga produk = selling_price); HPP/cost_price dihapus.
    assert "cost_price" not in ProductCreate.model_fields
    assert "cost_price" not in ProductUpdate.model_fields


@pytest.mark.asyncio
async def test_create_produk_tanpa_harga_tetap_valid():
    svc = _service()
    p = await svc.create(ProductCreate(code="A", name="A", unit="PCS"))
    assert p.selling_price is None


def test_harga_produk_negatif_ditolak_schema():
    with pytest.raises(ValidationError):
        ProductCreate(code="A", name="A", unit="PCS", selling_price=Decimal("-1"))
    with pytest.raises(ValidationError):
        ProductUpdate(selling_price=Decimal("-1"))


@pytest.mark.asyncio
async def test_update_harga_produk():
    svc = _service([FakeProduct(id="p1", code="A")])
    p = await svc.update("p1", ProductUpdate(selling_price=Decimal("7500")))
    assert p.selling_price == Decimal("7500")


@pytest.mark.asyncio
async def test_import_csv_kolom_harga_opsional():
    svc = _service()
    csv = (
        b"code,name,category,unit,selling_price\n"
        b"A,Produk A,RTD,PCS,6000\n"
        b"B,Produk B,RTD,PCS,\n"
    )
    assert (await svc.import_csv(csv))["imported"] == 2
    a = await svc._repo.get_by_code("A")
    b = await svc._repo.get_by_code("B")
    assert a.selling_price == Decimal("6000")
    assert b.selling_price is None


@pytest.mark.asyncio
async def test_import_csv_lama_dengan_kolom_cost_price_tetap_diterima():
    # Backward-compat: file CSV lama yang masih punya kolom cost_price tidak ditolak;
    # kolom itu diabaikan.
    svc = _service()
    csv = b"code,name,unit,cost_price,selling_price\nA,A,PCS,4500,6000\n"
    assert (await svc.import_csv(csv))["imported"] == 1
    a = await svc._repo.get_by_code("A")
    assert a.selling_price == Decimal("6000")
    assert not hasattr(a, "cost_price")


@pytest.mark.asyncio
async def test_import_csv_harga_bukan_angka_invalid_format():
    svc = _service()
    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(b"code,name,unit,selling_price\nA,A,PCS,mahal\n")


@pytest.mark.asyncio
async def test_import_csv_harga_negatif_invalid_format_bukan_500():
    svc = _service()
    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(b"code,name,unit,selling_price\nA,A,PCS,-1\n")
