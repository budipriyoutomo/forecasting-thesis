"""
Fase 3 — endpoint /api/v1/uploads (AGENTS.md §3, §4).

UploadService dirakit dari fake in-memory (tanpa DB/R2) lewat dependency_overrides.
Test wajib: happy path, auth failure (tanpa token / expired), UPLOAD_INVALID_FORMAT,
INSUFFICIENT_DATA, UPLOAD_FILE_TOO_LARGE, riwayat & detail (403 milik user lain).
"""
from unittest.mock import MagicMock

import pytest

from app.api.deps import get_upload_service
from app.main import app
from app.services.upload_service import UploadService
from tests.unit.test_upload_service import (
    FakeDemandRepo,
    FakeProductRepo,
    FakeSessionRepo,
)


def _make_service():
    storage = MagicMock()
    storage.upload_temp.return_value = "temp/uploads/x/f.csv"
    storage.move_to_permanent.return_value = "permanent/datasets/u/x/raw.csv"
    return UploadService(
        storage=storage,
        sessions=FakeSessionRepo(),
        demand=FakeDemandRepo(),
        products=FakeProductRepo(),
    )


@pytest.fixture
def upload_service():
    service = _make_service()
    app.dependency_overrides[get_upload_service] = lambda: service
    yield service
    app.dependency_overrides.pop(get_upload_service, None)


@pytest.mark.asyncio
async def test_upload_happy_path(client, auth_headers, valid_csv_bytes, upload_service):
    files = {"file": ("consumption.csv", valid_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["n_rows"] == 12
    assert body["data"]["n_products_detected"] == 3
    assert body["data"]["status"] == "validated"
    assert "session_id" in body["data"]
    assert isinstance(body["data"]["preview"], list)


@pytest.mark.asyncio
async def test_upload_without_auth(client, valid_csv_bytes, upload_service):
    files = {"file": ("consumption.csv", valid_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", files=files)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_upload_with_expired_token(client, expired_auth_headers, valid_csv_bytes, upload_service):
    files = {"file": ("consumption.csv", valid_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=expired_auth_headers, files=files)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_upload_invalid_file_extension(client, auth_headers, valid_csv_bytes, upload_service):
    files = {"file": ("consumption.txt", valid_csv_bytes, "text/plain")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UPLOAD_INVALID_FORMAT"


@pytest.mark.asyncio
async def test_upload_missing_required_column(client, auth_headers, missing_column_csv_bytes, upload_service):
    files = {"file": ("consumption.csv", missing_column_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UPLOAD_INVALID_FORMAT"
    assert "actual" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_upload_insufficient_data(client, auth_headers, too_few_rows_csv_bytes, upload_service):
    files = {"file": ("consumption.csv", too_few_rows_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_DATA"


@pytest.mark.asyncio
async def test_upload_file_too_large(client, auth_headers, upload_service):
    big = b"product_code,period,actual\n" + b"x" * (11 * 1024 * 1024)
    files = {"file": ("consumption.csv", big, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UPLOAD_FILE_TOO_LARGE"


@pytest.mark.asyncio
async def test_list_uploads(client, auth_headers, valid_csv_bytes, upload_service):
    files = {"file": ("consumption.csv", valid_csv_bytes, "text/csv")}
    await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    response = await client.get("/api/v1/uploads", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()["data"]
    assert len(data) == 1
    assert data[0]["file_name"] == "consumption.csv"


@pytest.mark.asyncio
async def test_get_upload_detail(client, auth_headers, valid_csv_bytes, upload_service):
    files = {"file": ("consumption.csv", valid_csv_bytes, "text/csv")}
    created = await client.post("/api/v1/uploads", headers=auth_headers, files=files)
    session_id = created.json()["data"]["session_id"]

    response = await client.get(f"/api/v1/uploads/{session_id}", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["data"]["session_id"] == session_id


@pytest.mark.asyncio
async def test_get_upload_not_found(client, auth_headers, upload_service):
    response = await client.get("/api/v1/uploads/00000000-0000-0000-0000-0000000000ff", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "SESSION_NOT_FOUND"
