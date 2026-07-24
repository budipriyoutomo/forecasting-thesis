"""
Fase 1 — SupabaseAuthenticator (verifikasi kredensial ke GoTrue), httpx di-mock.
"""
import httpx
import pytest

from app.config import get_settings
from app.services import supabase_auth as sa
from app.services.supabase_auth import (
    AuthProviderUnavailableError,
    Identity,
    SupabaseAuthenticator,
)
from app.utils.exceptions import InvalidCredentialsError

settings = get_settings()


class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeAsyncClient:
    """Mengganti httpx.AsyncClient — mengembalikan response yang sudah disiapkan."""

    response: _FakeResponse | None = None
    raise_exc: Exception | None = None
    last_request: dict | None = None

    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def post(self, url, params=None, headers=None, json=None):
        type(self).last_request = {"url": url, "params": params, "headers": headers, "json": json}
        if type(self).raise_exc:
            raise type(self).raise_exc
        return type(self).response


@pytest.fixture
def configured(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", "https://proj.supabase.co")
    monkeypatch.setattr(settings, "SUPABASE_KEY", "anon-key")
    _FakeAsyncClient.response = None
    _FakeAsyncClient.raise_exc = None
    _FakeAsyncClient.last_request = None
    monkeypatch.setattr(sa.httpx, "AsyncClient", _FakeAsyncClient)


@pytest.mark.asyncio
async def test_authenticate_belum_dikonfigurasi_raise(monkeypatch):
    monkeypatch.setattr(settings, "SUPABASE_URL", None)
    monkeypatch.setattr(settings, "SUPABASE_KEY", None)

    with pytest.raises(AuthProviderUnavailableError):
        await SupabaseAuthenticator().authenticate("a@b.com", "x")


@pytest.mark.asyncio
async def test_authenticate_sukses_kembalikan_identity(configured):
    _FakeAsyncClient.response = _FakeResponse(
        200, {"user": {"id": "abc-123", "email": "a@b.com"}, "access_token": "supa"}
    )

    identity = await SupabaseAuthenticator().authenticate("a@b.com", "correct")

    assert isinstance(identity, Identity)
    assert identity.id == "abc-123"
    assert _FakeAsyncClient.last_request["params"] == {"grant_type": "password"}
    assert _FakeAsyncClient.last_request["headers"]["apikey"] == "anon-key"


@pytest.mark.asyncio
async def test_authenticate_kredensial_salah_400_invalid(configured):
    _FakeAsyncClient.response = _FakeResponse(400, {"error": "invalid_grant"})

    with pytest.raises(InvalidCredentialsError):
        await SupabaseAuthenticator().authenticate("a@b.com", "wrong")


@pytest.mark.asyncio
async def test_authenticate_respons_tanpa_user_id_invalid(configured):
    _FakeAsyncClient.response = _FakeResponse(200, {"user": {}})

    with pytest.raises(InvalidCredentialsError):
        await SupabaseAuthenticator().authenticate("a@b.com", "correct")


@pytest.mark.asyncio
async def test_authenticate_error_jaringan_503(configured):
    _FakeAsyncClient.raise_exc = httpx.ConnectError("boom")

    with pytest.raises(AuthProviderUnavailableError):
        await SupabaseAuthenticator().authenticate("a@b.com", "correct")
