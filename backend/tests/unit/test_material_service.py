"""
Fase 2 — unit test MaterialService (CRUD + import), repository di-mock.
"""
from decimal import Decimal

import pytest

from app.schemas.material import MaterialCreate, MaterialUpdate
from app.services.material_service import MaterialService
from app.utils.exceptions import (
    MaterialCodeExistsError,
    MaterialNotFoundError,
    UploadInvalidFormatError,
)


class FakeMaterial:
    def __init__(self, **kw):
        self.id = kw.get("id", "m-" + kw["code"])
        self.code = kw["code"]
        self.name = kw.get("name", "")
        self.category = kw.get("category")
        self.unit = kw.get("unit", "kg")
        self.lead_time_days = kw.get("lead_time_days", 0)
        self.moq = kw.get("moq", Decimal(0))
        self.manual_safety_stock = kw.get("manual_safety_stock")


class FakeMaterialRepository:
    """Repo in-memory; menirukan keunikan `code`."""

    def __init__(self, materials=None):
        self._items = {m.id: m for m in (materials or [])}

    async def list(self):
        return sorted(self._items.values(), key=lambda m: m.code)

    async def get_by_id(self, material_id):
        return self._items.get(material_id)

    async def get_by_code(self, code):
        return next((m for m in self._items.values() if m.code == code), None)

    async def add(self, material):
        material.id = material.id or ("m-" + material.code)
        self._items[material.id] = material
        return material

    async def save(self, material):
        self._items[material.id] = material
        return material

    async def delete(self, material):
        self._items.pop(material.id, None)


def _service(materials=None):
    # model_factory dipakai service untuk membuat instance ORM; di test pakai FakeMaterial.
    return MaterialService(FakeMaterialRepository(materials), model_factory=FakeMaterial)


@pytest.mark.asyncio
async def test_create_happy_path():
    svc = _service()
    payload = MaterialCreate(code="RM-001", name="Tepung", unit="kg", lead_time_days=7, moq=Decimal(100))

    created = await svc.create(payload)

    assert created.code == "RM-001"
    assert (await svc.list())[0].code == "RM-001"


@pytest.mark.asyncio
async def test_create_kode_duplikat_ditolak():
    svc = _service([FakeMaterial(code="RM-001", name="Tepung", unit="kg")])
    payload = MaterialCreate(code="RM-001", name="Lain", unit="kg")

    with pytest.raises(MaterialCodeExistsError):
        await svc.create(payload)


@pytest.mark.asyncio
async def test_get_tidak_ada_404():
    svc = _service()
    with pytest.raises(MaterialNotFoundError):
        await svc.get("tidak-ada")


@pytest.mark.asyncio
async def test_update_happy_path():
    svc = _service([FakeMaterial(id="m1", code="RM-001", name="Tepung", unit="kg")])

    updated = await svc.update("m1", MaterialUpdate(name="Tepung Terigu", lead_time_days=14))

    assert updated.name == "Tepung Terigu"
    assert updated.lead_time_days == 14


@pytest.mark.asyncio
async def test_update_ganti_kode_ke_yang_sudah_dipakai_ditolak():
    svc = _service(
        [
            FakeMaterial(id="m1", code="RM-001", name="A", unit="kg"),
            FakeMaterial(id="m2", code="RM-002", name="B", unit="kg"),
        ]
    )
    with pytest.raises(MaterialCodeExistsError):
        await svc.update("m2", MaterialUpdate(code="RM-001"))


@pytest.mark.asyncio
async def test_update_tidak_ada_404():
    svc = _service()
    with pytest.raises(MaterialNotFoundError):
        await svc.update("x", MaterialUpdate(name="Z"))


@pytest.mark.asyncio
async def test_delete_happy_path():
    svc = _service([FakeMaterial(id="m1", code="RM-001", name="A", unit="kg")])

    await svc.delete("m1")

    assert await svc.list() == []


@pytest.mark.asyncio
async def test_delete_tidak_ada_404():
    svc = _service()
    with pytest.raises(MaterialNotFoundError):
        await svc.delete("x")


@pytest.mark.asyncio
async def test_import_csv_menambah_banyak_material():
    svc = _service()
    csv = (
        "code,name,category,unit,lead_time_days,moq,manual_safety_stock\n"
        "RM-001,Tepung,Bahan,kg,7,100,10\n"
        "RM-002,Gula,Bahan,kg,5,50,\n"
    ).encode("utf-8")

    result = await svc.import_csv(csv)

    assert result["imported"] == 2
    codes = {m.code for m in await svc.list()}
    assert codes == {"RM-001", "RM-002"}


@pytest.mark.asyncio
async def test_import_csv_kolom_wajib_hilang_invalid_format():
    svc = _service()
    csv = b"code,name\nRM-001,Tepung\n"  # 'unit' hilang

    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(csv)


@pytest.mark.asyncio
async def test_import_csv_kode_duplikat_dalam_file_ditolak():
    svc = _service()
    csv = b"code,name,unit\nRM-001,Tepung,kg\nRM-001,Gula,kg\n"

    with pytest.raises(MaterialCodeExistsError):
        await svc.import_csv(csv)


@pytest.mark.asyncio
async def test_import_csv_moq_bukan_angka_invalid_format():
    svc = _service()
    csv = b"code,name,unit,moq\nRM-001,Tepung,kg,bukan-angka\n"

    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(csv)


@pytest.mark.asyncio
async def test_import_csv_lead_time_bukan_int_invalid_format():
    svc = _service()
    csv = b"code,name,unit,lead_time_days\nRM-001,Tepung,kg,7.5\n"

    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(csv)


@pytest.mark.asyncio
async def test_import_csv_field_wajib_kosong_invalid_format():
    svc = _service()
    csv = b"code,name,unit\nRM-001,,kg\n"  # name kosong

    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(csv)


@pytest.mark.asyncio
async def test_import_csv_file_tanpa_baris_data_invalid_format():
    svc = _service()
    csv = b"code,name,unit\n"

    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(csv)


@pytest.mark.asyncio
async def test_import_csv_bukan_utf8_invalid_format():
    svc = _service()

    with pytest.raises(UploadInvalidFormatError):
        await svc.import_csv(b"code,name,unit\n\xff\xfeRM,Tepung,kg\n")


@pytest.mark.asyncio
async def test_get_happy_path():
    svc = _service([FakeMaterial(id="m1", code="RM-001", name="Tepung", unit="kg")])

    material = await svc.get("m1")

    assert material.code == "RM-001"
