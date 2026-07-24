"""
Fase 2 — endpoint /api/v1/materials (AGENTS.md §3, §4).

RBAC: GET boleh semua role terautentikasi; POST/PUT/DELETE/import hanya admin.
MaterialService di-override lewat dependency_overrides.
"""
from decimal import Decimal

import jwt
import pytest

from app.api.deps import get_material_service
from app.config import get_settings
from app.main import app
from tests.unit.test_material_service import FakeMaterial, FakeMaterialRepository
from app.services.material_service import MaterialService

settings = get_settings()


def _token(role: str) -> str:
    from datetime import datetime, timedelta, timezone

    payload = {
        "sub": "00000000-0000-0000-0000-000000000009",
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=1),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _headers(role: str) -> dict:
    return {"Authorization": f"Bearer {_token(role)}"}


def _override(materials=None):
    def _factory():
        return MaterialService(FakeMaterialRepository(materials or []), model_factory=FakeMaterial)

    app.dependency_overrides[get_material_service] = _factory


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_material_service, None)


@pytest.mark.asyncio
async def test_list_materials_terautentikasi(client):
    _override([FakeMaterial(id="m1", code="RM-001", name="Tepung", unit="kg")])

    res = await client.get("/api/v1/materials", headers=_headers("viewer"))

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"][0]["code"] == "RM-001"


@pytest.mark.asyncio
async def test_list_tanpa_token_401(client):
    _override([])
    res = await client.get("/api/v1/materials")
    assert res.status_code == 401


@pytest.mark.asyncio
async def test_get_material_by_id(client):
    _override([FakeMaterial(id="m1", code="RM-001", name="Tepung", unit="kg")])

    res = await client.get("/api/v1/materials/m1", headers=_headers("ppic"))

    assert res.status_code == 200
    assert res.json()["data"]["code"] == "RM-001"


@pytest.mark.asyncio
async def test_get_material_tidak_ada_404(client):
    _override([])

    res = await client.get("/api/v1/materials/none", headers=_headers("ppic"))

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "MATERIAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_create_material_admin_201(client):
    _override([])

    res = await client.post(
        "/api/v1/materials",
        headers=_headers("admin"),
        json={"code": "RM-010", "name": "Garam", "unit": "kg", "lead_time_days": 3, "moq": 20},
    )

    assert res.status_code == 201
    assert res.json()["data"]["code"] == "RM-010"


@pytest.mark.asyncio
async def test_create_material_non_admin_403(client):
    _override([])

    res = await client.post(
        "/api/v1/materials",
        headers=_headers("ppic"),
        json={"code": "RM-010", "name": "Garam", "unit": "kg"},
    )

    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"


@pytest.mark.asyncio
async def test_create_kode_duplikat_409(client):
    _override([FakeMaterial(id="m1", code="RM-001", name="Tepung", unit="kg")])

    res = await client.post(
        "/api/v1/materials",
        headers=_headers("admin"),
        json={"code": "RM-001", "name": "Lain", "unit": "kg"},
    )

    assert res.status_code == 409
    assert res.json()["error"]["code"] == "MATERIAL_CODE_EXISTS"


@pytest.mark.asyncio
async def test_update_material_admin(client):
    _override([FakeMaterial(id="m1", code="RM-001", name="Tepung", unit="kg")])

    res = await client.put(
        "/api/v1/materials/m1", headers=_headers("admin"), json={"name": "Tepung Terigu"}
    )

    assert res.status_code == 200
    assert res.json()["data"]["name"] == "Tepung Terigu"


@pytest.mark.asyncio
async def test_update_tidak_ada_404(client):
    _override([])

    res = await client.put("/api/v1/materials/none", headers=_headers("admin"), json={"name": "X"})

    assert res.status_code == 404
    assert res.json()["error"]["code"] == "MATERIAL_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete_material_admin(client):
    _override([FakeMaterial(id="m1", code="RM-001", name="Tepung", unit="kg")])

    res = await client.delete("/api/v1/materials/m1", headers=_headers("admin"))

    assert res.status_code == 200


@pytest.mark.asyncio
async def test_delete_non_admin_403(client):
    _override([FakeMaterial(id="m1", code="RM-001", name="Tepung", unit="kg")])

    res = await client.delete("/api/v1/materials/m1", headers=_headers("purchasing"))

    assert res.status_code == 403


@pytest.mark.asyncio
async def test_import_csv_admin(client):
    _override([])
    csv = b"code,name,unit,lead_time_days,moq\nRM-100,Tepung,kg,7,100\nRM-101,Gula,kg,5,50\n"

    res = await client.post(
        "/api/v1/materials/import",
        headers=_headers("admin"),
        files={"file": ("materials.csv", csv, "text/csv")},
    )

    assert res.status_code == 200
    assert res.json()["data"]["imported"] == 2


@pytest.mark.asyncio
async def test_import_csv_non_admin_403(client):
    _override([])
    csv = b"code,name,unit\nRM-100,Tepung,kg\n"

    res = await client.post(
        "/api/v1/materials/import",
        headers=_headers("viewer"),
        files={"file": ("materials.csv", csv, "text/csv")},
    )

    assert res.status_code == 403
