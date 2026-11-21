"""
User Management (CR v3.7, 21 Nov 2026) — endpoint /users. Semua (termasuk GET) khusus admin
(`user.manage`): daftar user berisi email pribadi, beda dengan GET master data yang terbuka.
"""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.api.deps import get_user_service
from app.config import get_settings
from app.main import app
from app.services.user_service import UserService
from tests.unit.test_user_service import ADMIN_ID, PPIC_ID, FakeUserRepo, _user

settings = get_settings()
BASE = "/api/v1/users"


def _headers(role: str, sub: str = ADMIN_ID) -> dict:
    payload = {"sub": sub, "role": role, "exp": datetime.now(timezone.utc) + timedelta(hours=1)}
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def repo():
    r = FakeUserRepo([_user(ADMIN_ID, "admin@x.com", "admin"), _user(PPIC_ID, "ppic@x.com", "ppic")])
    app.dependency_overrides[get_user_service] = lambda: UserService(r)
    yield r
    app.dependency_overrides.pop(get_user_service, None)


@pytest.mark.asyncio
async def test_list_admin_200_dengan_status_aktif(client, repo):
    res = await client.get(BASE, headers=_headers("admin"))

    assert res.status_code == 200
    data = res.json()["data"]
    assert [u["email"] for u in data] == ["admin@x.com", "ppic@x.com"]
    assert set(data[0]) >= {"id", "email", "name", "role", "is_verified", "is_active"}


@pytest.mark.asyncio
@pytest.mark.parametrize("role", ["ppic", "purchasing", "viewer"])
async def test_list_non_admin_403(client, repo, role):
    res = await client.get(BASE, headers=_headers(role))
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "AUTH_FORBIDDEN"


@pytest.mark.asyncio
async def test_list_tanpa_token_401(client, repo):
    assert (await client.get(BASE)).status_code == 401


@pytest.mark.asyncio
async def test_create_201(client, repo):
    res = await client.post(BASE, headers=_headers("admin"),
                            json={"email": "Baru@X.com", "name": "Baru", "role": "purchasing"})

    assert res.status_code == 201
    body = res.json()
    assert body["success"] is True
    assert body["data"]["email"] == "baru@x.com"
    assert body["data"]["role"] == "purchasing"
    assert body["data"]["is_active"] is True


@pytest.mark.asyncio
async def test_create_email_duplikat_409(client, repo):
    res = await client.post(BASE, headers=_headers("admin"),
                            json={"email": "ppic@x.com", "name": "X", "role": "viewer"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "USER_EMAIL_EXISTS"


@pytest.mark.asyncio
async def test_create_role_tidak_valid_422(client, repo):
    res = await client.post(BASE, headers=_headers("admin"),
                            json={"email": "a@b.com", "name": "X", "role": "root"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


@pytest.mark.asyncio
async def test_update_role_user_lain_200(client, repo):
    res = await client.put(f"{BASE}/{PPIC_ID}", headers=_headers("admin"), json={"role": "viewer", "is_active": False})

    assert res.status_code == 200
    assert res.json()["data"]["role"] == "viewer"
    assert res.json()["data"]["is_active"] is False


@pytest.mark.asyncio
async def test_update_diri_sendiri_turun_role_422(client, repo):
    res = await client.put(f"{BASE}/{ADMIN_ID}", headers=_headers("admin"), json={"role": "viewer"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "USER_SELF_LOCKOUT"


@pytest.mark.asyncio
async def test_update_tidak_ditemukan_404(client, repo):
    res = await client.put(f"{BASE}/33333333-3333-3333-3333-333333333333", headers=_headers("admin"), json={"role": "viewer"})
    assert res.status_code == 404
    assert res.json()["error"]["code"] == "USER_NOT_FOUND"
