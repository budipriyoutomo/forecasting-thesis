"""
Fase 1 — endpoint /api/v1/auth/login & /me (AGENTS.md §3, §4).

AuthService di-override lewat FastAPI dependency_overrides supaya tidak butuh
DB/Supabase nyata. Test wajib: happy path, 401 kredensial salah, 403 belum
verified, 401 tanpa token, 401 token expired, /me happy path.
"""
import uuid

import pytest

from app.api.deps import get_auth_service
from app.main import app
from app.services.auth_service import AuthService, Identity
from app.utils.exceptions import InvalidCredentialsError

UID = uuid.UUID("22222222-2222-2222-2222-222222222222")


class FakeUser:
    def __init__(self, id, email, name, role, is_verified):
        self.id = id
        self.email = email
        self.name = name
        self.role = role
        self.is_verified = is_verified


class FakeUserRepository:
    def __init__(self, users):
        self._by_email = {u.email: u for u in users}
        self._by_id = {str(u.id): u for u in users}

    async def get_by_email(self, email):
        return self._by_email.get(email)

    async def get_by_id(self, user_id):
        return self._by_id.get(str(user_id))


class FakeAuthenticator:
    async def authenticate(self, email, password):
        if password != "correct":
            raise InvalidCredentialsError("email atau password salah")
        return Identity(id=email, email=email)


def _override_service(users):
    def _factory():
        return AuthService(FakeUserRepository(users), FakeAuthenticator())

    app.dependency_overrides[get_auth_service] = _factory


@pytest.fixture(autouse=True)
def _clear_overrides():
    yield
    app.dependency_overrides.pop(get_auth_service, None)


@pytest.mark.asyncio
async def test_login_happy_path(client):
    _override_service([FakeUser(UID, "planner@corp.com", "Planner", "ppic", True)])

    res = await client.post("/api/v1/auth/login", json={"email": "planner@corp.com", "password": "correct"})

    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["token_type"] == "bearer"
    assert body["data"]["access_token"]
    assert body["data"]["user"]["role"] == "ppic"
    assert body["data"]["user"]["id"] == str(UID)


@pytest.mark.asyncio
async def test_login_kredensial_salah_401(client):
    _override_service([FakeUser(UID, "planner@corp.com", "Planner", "ppic", True)])

    res = await client.post("/api/v1/auth/login", json={"email": "planner@corp.com", "password": "salah"})

    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_login_email_belum_verified_403(client):
    _override_service([FakeUser(UID, "new@corp.com", "New", "viewer", False)])

    res = await client.post("/api/v1/auth/login", json={"email": "new@corp.com", "password": "correct"})

    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_EMAIL_NOT_VERIFIED"


@pytest.mark.asyncio
async def test_login_email_format_salah_422(client):
    _override_service([])

    res = await client.post("/api/v1/auth/login", json={"email": "bukan-email", "password": "x"})

    assert res.status_code == 422  # validation Pydantic (EmailStr)


@pytest.mark.asyncio
async def test_me_happy_path(client, auth_headers):
    # token di auth_headers punya sub=00000000-...-0001, role=ppic (conftest)
    uid = "00000000-0000-0000-0000-000000000001"
    _override_service([FakeUser(uuid.UUID(uid), "me@corp.com", "Me", "ppic", True)])

    res = await client.get("/api/v1/auth/me", headers=auth_headers)

    assert res.status_code == 200
    assert res.json()["data"]["email"] == "me@corp.com"


@pytest.mark.asyncio
async def test_me_tanpa_token_401(client):
    res = await client.get("/api/v1/auth/me")

    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_me_token_expired_401(client, expired_auth_headers):
    res = await client.get("/api/v1/auth/me", headers=expired_auth_headers)

    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_TOKEN_EXPIRED"
