"""
🔴 RED → 🟢 GREEN → 🔵 REFACTOR contoh untuk POST /api/v1/uploads

Ini adalah siklus TDD acuan (AGENTS.md §3) untuk fitur-fitur berikutnya.
Test wajib per endpoint (checklist AGENTS.md §3):
  - happy path
  - auth failure (tanpa token, token expired)
  - validation error (format salah, kolom hilang)
  - insufficient data
Forbidden/not-found/engine-failure belum relevan untuk endpoint ini
(tidak ada resource kepemilikan atau forecasting engine di alur upload).
"""
import pytest


@pytest.mark.asyncio
async def test_upload_happy_path(client, auth_headers, valid_csv_bytes):
    files = {"file": ("consumption.csv", valid_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["n_rows"] == 12
    assert body["data"]["n_materials_detected"] == 3
    assert body["data"]["status"] == "validated"
    assert "session_id" in body["data"]
    assert isinstance(body["data"]["preview"], list)


@pytest.mark.asyncio
async def test_upload_without_auth(client, valid_csv_bytes):
    files = {"file": ("consumption.csv", valid_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", files=files)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_upload_with_expired_token(client, expired_auth_headers, valid_csv_bytes):
    files = {"file": ("consumption.csv", valid_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=expired_auth_headers, files=files)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "AUTH_TOKEN_EXPIRED"


@pytest.mark.asyncio
async def test_upload_invalid_file_extension(client, auth_headers, valid_csv_bytes):
    files = {"file": ("consumption.txt", valid_csv_bytes, "text/plain")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UPLOAD_INVALID_FORMAT"


@pytest.mark.asyncio
async def test_upload_missing_required_column(client, auth_headers, missing_column_csv_bytes):
    files = {"file": ("consumption.csv", missing_column_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UPLOAD_INVALID_FORMAT"
    assert "quantity" in response.json()["error"]["message"]


@pytest.mark.asyncio
async def test_upload_insufficient_data(client, auth_headers, too_few_rows_csv_bytes):
    files = {"file": ("consumption.csv", too_few_rows_csv_bytes, "text/csv")}
    response = await client.post("/api/v1/uploads", headers=auth_headers, files=files)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "INSUFFICIENT_DATA"
