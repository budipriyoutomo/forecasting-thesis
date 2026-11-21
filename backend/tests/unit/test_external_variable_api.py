"""Fase 11.2b — endpoint /external-variables. RBAC: baca semua role, tulis admin."""
from datetime import date, datetime, timedelta, timezone

import jwt
import pytest

from app.api.deps import get_external_variable_service
from app.config import get_settings
from app.main import app
from app.services.external_variable_service import ExternalVariableService
from tests.unit.test_external_variable_service import (
    P1,
    FakeDemand,
    FakeProducts,
    FakeVarRepo,
    _val,
    _val_factory,
    _var,
    _var_factory,
)

settings = get_settings()
BASE = "/api/v1/external-variables"


def _headers(role: str) -> dict:
    payload = {"sub": "00000000-0000-0000-0000-000000000009", "role": role,
               "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    return {"Authorization": f"Bearer {jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)}"}


def _override(variables=None, values=None, demand=None):
    repo = FakeVarRepo(variables, values)
    app.dependency_overrides[get_external_variable_service] = lambda: ExternalVariableService(
        repo, FakeProducts([P1]), demand=demand or FakeDemand(), var_factory=_var_factory, value_factory=_val_factory
    )
    return repo


@pytest.fixture(autouse=True)
def _clear():
    yield
    app.dependency_overrides.pop(get_external_variable_service, None)


@pytest.mark.asyncio
async def test_list_dengan_jumlah_nilai(client):
    _override([_var("v1", "suhu")], [_val("v1", date(2026, 1, 1), 30)])
    res = await client.get(BASE, headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.json()["data"][0]["code"] == "suhu"
    assert res.json()["data"][0]["n_values"] == 1


@pytest.mark.asyncio
async def test_tanpa_token_401(client):
    _override()
    assert (await client.get(BASE)).status_code == 401


@pytest.mark.asyncio
async def test_create_admin_201_dan_duplikat_409(client):
    _override([_var("v1", "suhu")])
    body = {"code": "promo", "name": "Promosi", "value_type": "flag", "scope": "product"}
    res = await client.post(BASE, json=body, headers=_headers("admin"))
    assert res.status_code == 201
    assert res.json()["data"]["is_active"] is True

    res = await client.post(BASE, json={"code": "suhu", "name": "x"}, headers=_headers("admin"))
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "EXTERNAL_VARIABLE_CODE_EXISTS"


@pytest.mark.asyncio
async def test_create_non_admin_403_dan_kode_invalid_422(client):
    _override()
    assert (await client.post(BASE, json={"code": "a", "name": "x"}, headers=_headers("viewer"))).status_code == 403
    assert (await client.post(BASE, json={"code": "Bad Code", "name": "x"}, headers=_headers("admin"))).status_code == 422


@pytest.mark.asyncio
async def test_toggle_aktif_dan_404(client):
    _override([_var("v1", "suhu")])
    res = await client.put(f"{BASE}/v1", json={"is_active": False}, headers=_headers("admin"))
    assert res.json()["data"]["is_active"] is False

    res = await client.put(f"{BASE}/nope", json={"is_active": False}, headers=_headers("admin"))
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "EXTERNAL_VARIABLE_NOT_FOUND"


@pytest.mark.asyncio
async def test_delete(client):
    repo = _override([_var("v1", "suhu")])
    res = await client.delete(f"{BASE}/v1", headers=_headers("admin"))
    assert res.status_code == 200 and repo.vars == {}


@pytest.mark.asyncio
async def test_import_pesan_menyebut_normalisasi_periode(client):
    _override([_var("v1", "suhu")])
    body = b"variable_code,period,value\nsuhu,2024-01-24,27.2\nsuhu,2024-01-24,27.5\n"
    files = {"file": ("nilai.csv", body, "text/csv")}
    res = await client.post(f"{BASE}/values/import", files=files, headers=_headers("admin"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert (data["imported"], data["normalized"], data["overwritten"]) == (1, 2, 1)
    assert res.json()["message"] == "1 nilai diimpor (2 periode digeser ke awal bulan, 1 baris ganda ditimpa)"


@pytest.mark.asyncio
async def test_import_nilai_dan_list_nilai(client):
    _override([_var("v1", "suhu")])
    files = {"file": ("nilai.csv", b"variable_code,period,value\nsuhu,2026-01-01,30\n", "text/csv")}
    res = await client.post(f"{BASE}/values/import", files=files, headers=_headers("admin"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert (data["imported"], data["normalized"], data["overwritten"]) == (1, 0, 0)
    assert data["format"] == "long" and data["skipped"] == {} and data["warnings"] == []

    res = await client.get(f"{BASE}/v1/values", headers=_headers("viewer"))
    assert res.json()["data"] == [{"product_id": None, "period": "2026-01-01", "value": 30.0}]


@pytest.mark.asyncio
async def test_import_invalid_400(client):
    _override()
    files = {"file": ("nilai.csv", b"variable_code,period,value\nhujan,2026-01-01,1\n", "text/csv")}
    res = await client.post(f"{BASE}/values/import", files=files, headers=_headers("admin"))
    assert res.status_code == 400
    assert res.json()["error"]["code"] == "UPLOAD_INVALID_FORMAT"


@pytest.mark.asyncio
async def test_ubah_nilai_per_periode(client):
    repo = _override([_var("v1", "suhu")], [_val("v1", date(2026, 1, 1), 30)])
    body = {"values": [{"period": "2026-01-01", "value": 31}, {"period": "2026-02-01", "value": 28}]}
    res = await client.put(f"{BASE}/v1/values", json=body, headers=_headers("ppic"))
    assert res.status_code == 200
    assert res.json()["data"] == {"id": "v1", "updated": 2}
    assert sorted((r.period.isoformat(), r.value) for r in repo.values) == [("2026-01-01", 31), ("2026-02-01", 28)]


@pytest.mark.asyncio
async def test_ubah_nilai_rbac_dan_validasi(client):
    _override([_var("v1", "promo", value_type="flag")])
    body = {"values": [{"period": "2026-01-01", "value": 1}]}
    assert (await client.put(f"{BASE}/v1/values", json=body, headers=_headers("viewer"))).status_code == 403
    assert (await client.put(f"{BASE}/v1/values", json={"values": []}, headers=_headers("admin"))).status_code == 422
    bad = {"values": [{"period": "2026-01-01", "value": 5}]}
    res = await client.put(f"{BASE}/v1/values", json=bad, headers=_headers("admin"))
    assert res.status_code == 400 and res.json()["error"]["code"] == "UPLOAD_INVALID_FORMAT"


@pytest.mark.asyncio
async def test_hapus_semua_nilai(client):
    repo = _override([_var("v1", "suhu")], [_val("v1", date(2026, 1, 1), 30)])
    res = await client.delete(f"{BASE}/v1/values", headers=_headers("admin"))
    assert res.json()["data"] == {"id": "v1", "deleted_values": 1}
    assert repo.values == []


@pytest.mark.asyncio
async def test_coverage_endpoint(client):
    _override(
        [_var("v1", "suhu")],
        [_val("v1", date(2024, 1, 1), 27), _val("v1", date(2024, 2, 1), 28)],
        demand=FakeDemand(date(2024, 1, 1), date(2024, 2, 1)),
    )
    res = await client.get(f"{BASE}/coverage?horizon=1", headers=_headers("viewer"))
    assert res.status_code == 200
    [c] = res.json()["data"]
    assert c["code"] == "suhu" and c["n_expected"] == 3 and c["n_filled"] == 2
    assert c["missing_periods"] == ["2024-03-01"]


@pytest.mark.asyncio
async def test_coverage_horizon_tidak_valid_422(client):
    _override()
    res = await client.get(f"{BASE}/coverage?horizon=0", headers=_headers("viewer"))
    assert res.status_code == 422


@pytest.mark.asyncio
async def test_import_dry_run_tidak_menulis_dan_kembalikan_semua_error(client):
    repo = _override([_var("v1", "suhu")])
    body = b"variable_code,period,value\nsuhu,2024-01-01,27\nhujan,2024-01-01,1\nsuhu,x,1\n"
    files = {"file": ("nilai.csv", body, "text/csv")}
    res = await client.post(f"{BASE}/values/import?dry_run=true", files=files, headers=_headers("admin"))
    assert res.status_code == 200
    data = res.json()["data"]
    assert data["dry_run"] is True and data["valid"] is False and data["n_errors"] == 2
    assert res.json()["message"] == "Validasi: 2 error, 1 nilai siap diimpor"
    assert repo.values == []


@pytest.mark.asyncio
async def test_template_xlsx(client):
    _override([_var("v1", "suhu")], demand=FakeDemand(date(2024, 1, 1), date(2024, 1, 1)))
    res = await client.get(f"{BASE}/template?horizon=2", headers=_headers("viewer"))
    assert res.status_code == 200
    assert res.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert 'filename="template_variabel_eksternal.xlsx"' in res.headers["content-disposition"]
