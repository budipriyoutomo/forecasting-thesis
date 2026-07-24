"""
Fase 1 — unit test AuthService (docs/TASK_BREAKDOWN.md, AGENTS.md §3).

Repository & authenticator di-mock (fake in-memory) sesuai strategi coverage
services (mock, tanpa DB/Supabase nyata).
"""
import uuid

import jwt
import pytest

from app.config import get_settings
from app.services.auth_service import AuthService, Identity
from app.utils.exceptions import AuthEmailNotVerifiedError, InvalidCredentialsError

settings = get_settings()


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
    """Mensimulasikan Supabase Auth: hanya email dgn password 'correct' yang lolos."""

    async def authenticate(self, email, password):
        if password != "correct":
            raise InvalidCredentialsError("email atau password salah")
        return Identity(id=email, email=email)


UID = uuid.UUID("11111111-1111-1111-1111-111111111111")


def _service(users):
    return AuthService(FakeUserRepository(users), FakeAuthenticator())


@pytest.mark.asyncio
async def test_login_happy_path_mengeluarkan_jwt_valid():
    user = FakeUser(UID, "planner@corp.com", "Planner", "ppic", True)
    svc = _service([user])

    token, returned = await svc.login("planner@corp.com", "correct")

    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    assert payload["sub"] == str(UID)
    assert payload["role"] == "ppic"
    assert returned.email == "planner@corp.com"


@pytest.mark.asyncio
async def test_login_password_salah_invalid_credentials():
    user = FakeUser(UID, "planner@corp.com", "Planner", "ppic", True)
    svc = _service([user])

    with pytest.raises(InvalidCredentialsError):
        await svc.login("planner@corp.com", "wrong")


@pytest.mark.asyncio
async def test_login_user_tak_ada_di_profil_invalid_credentials():
    # Kredensial Supabase valid tapi profil belum ada di tabel users → tolak.
    svc = _service([])

    with pytest.raises(InvalidCredentialsError):
        await svc.login("ghost@corp.com", "correct")


@pytest.mark.asyncio
async def test_login_email_belum_verified_ditolak():
    user = FakeUser(UID, "new@corp.com", "New", "viewer", False)
    svc = _service([user])

    with pytest.raises(AuthEmailNotVerifiedError):
        await svc.login("new@corp.com", "correct")


@pytest.mark.asyncio
async def test_get_profile_by_id():
    user = FakeUser(UID, "planner@corp.com", "Planner", "ppic", True)
    svc = _service([user])

    profile = await svc.get_profile(str(UID))

    assert profile.email == "planner@corp.com"


@pytest.mark.asyncio
async def test_get_profile_tidak_ada_invalid_credentials():
    svc = _service([])

    with pytest.raises(InvalidCredentialsError):
        await svc.get_profile("00000000-0000-0000-0000-000000000000")
