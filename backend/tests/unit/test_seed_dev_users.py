"""
Unit test seeding user demo (app/scripts/seed_dev_users.py).

Repository di-fake (in-memory) — pola sama seperti tests/unit/test_auth_service.py.
"""
import pytest

from app.models.user import VALID_ROLES
from app.scripts.seed_dev_users import DEMO_USERS, seed_users


class FakeUser:
    def __init__(self, email, name, role, is_verified):
        self.email = email
        self.name = name
        self.role = role
        self.is_verified = is_verified


class FakeUserRepository:
    def __init__(self, existing=()):
        self._by_email = {u.email: u for u in existing}

    async def get_by_email(self, email):
        return self._by_email.get(email)

    async def create(self, *, email, name, role, is_verified):
        user = FakeUser(email, name, role, is_verified)
        self._by_email[email] = user
        return user


def test_semua_user_demo_punya_role_valid():
    for spec in DEMO_USERS:
        assert spec.role in VALID_ROLES


def test_role_user_demo_mencakup_semua_role():
    assert {spec.role for spec in DEMO_USERS} == set(VALID_ROLES)


@pytest.mark.asyncio
async def test_seed_membuat_semua_user_demo():
    repo = FakeUserRepository()

    created, skipped = await seed_users(repo)

    assert len(created) == len(DEMO_USERS)
    assert skipped == []
    for spec in DEMO_USERS:
        user = await repo.get_by_email(spec.email)
        assert user.role == spec.role
        # Wajib verified, kalau tidak AuthService menolak login (AuthEmailNotVerifiedError).
        assert user.is_verified is True


@pytest.mark.asyncio
async def test_seed_idempoten_tidak_menduplikasi_user_yang_ada():
    existing = FakeUser(DEMO_USERS[0].email, "Nama Lama", DEMO_USERS[0].role, True)
    repo = FakeUserRepository([existing])

    created, skipped = await seed_users(repo)

    assert skipped == [DEMO_USERS[0].email]
    assert len(created) == len(DEMO_USERS) - 1
    # User yang sudah ada tidak ditimpa.
    assert (await repo.get_by_email(DEMO_USERS[0].email)).name == "Nama Lama"
