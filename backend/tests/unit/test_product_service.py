"""Fase 2 v3.0 — unit test ProductService (CRUD + import), repository di-mock."""
import pytest

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
