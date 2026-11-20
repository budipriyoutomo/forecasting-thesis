"""
CR v3.5 §1 — semua error (validasi Pydantic, HTTPException Starlette, exception tak
tertangani) wajib memakai envelope `{success: false, error: {code, message}}`
(AGENTS.md §4), bukan `{"detail": ...}` bawaan FastAPI atau teks polos.
"""
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_product_service
from app.main import app
from tests.unit.test_external_variable_api import _headers, _override


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_validasi_pydantic_422_pakai_envelope_dan_pesan_indonesia(client):
    _override()
    res = await client.post(
        "/api/v1/external-variables", json={"code": "Bad Code", "name": "x"}, headers=_headers("admin")
    )

    assert res.status_code == 422
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    # Nama field diprefix, prefix "Value error, " Pydantic dibuang.
    assert body["error"]["message"].startswith("code: ")
    assert "Value error" not in body["error"]["message"]
    assert "detail" not in body


@pytest.mark.asyncio
async def test_validasi_query_param_422_envelope(client, auth_headers):
    res = await client.get("/api/v1/overrides/reorder?run_id=r1", headers=auth_headers)

    assert res.status_code == 422
    assert res.json()["success"] is False
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_route_tidak_ada_404_envelope(client):
    res = await client.get("/api/v1/tidak-ada")

    assert res.status_code == 404
    assert res.json() == {"success": False, "error": {"code": "HTTP_404", "message": "Not Found"}}


@pytest.mark.asyncio
async def test_method_tidak_diizinkan_405_envelope(client):
    res = await client.delete("/health")

    assert res.status_code == 405
    assert res.json()["error"]["code"] == "HTTP_405"


class _Boom:
    async def list(self):
        raise RuntimeError("rahasia internal: koneksi db=postgres://user:pass@host")


@pytest_asyncio.fixture
async def lenient_client():
    # raise_app_exceptions=False: ServerErrorMiddleware Starlette me-re-raise exception
    # sesudah mengirim response 500; kita ingin memeriksa response-nya.
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_exception_tak_tertangani_500_envelope_tanpa_stack_trace(lenient_client, auth_headers):
    app.dependency_overrides[get_product_service] = lambda: _Boom()

    res = await lenient_client.get("/api/v1/products", headers=auth_headers)

    assert res.status_code == 500
    assert res.json() == {
        "success": False,
        "error": {"code": "INTERNAL_ERROR", "message": "Terjadi kesalahan di server."},
    }
    assert "rahasia" not in res.text
