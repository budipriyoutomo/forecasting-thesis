"""
User Management (CR v3.7, 21 Nov 2026) — UserService: daftar, tambah profil, ubah role/status.

Kredensial tetap di Supabase Auth; service ini hanya mengelola profil + role di tabel `users`.
Pengaman: admin tidak bisa menurunkan role atau menonaktifkan dirinya sendiri (sistem tidak
boleh kehilangan admin — aktor selalu admin aktif, jadi minimal satu admin tersisa).
"""
import uuid
from types import SimpleNamespace

import pytest

from app.schemas.user import UserCreate, UserUpdate
from app.services.user_service import UserService
from app.utils.exceptions import UserEmailExistsError, UserNotFoundError, UserSelfLockoutError

ADMIN_ID = "11111111-1111-1111-1111-111111111111"
PPIC_ID = "22222222-2222-2222-2222-222222222222"


def _user(id, email, role, is_active=True, name="User"):
    return SimpleNamespace(id=uuid.UUID(id), email=email, name=name, role=role,
                           is_verified=True, is_active=is_active, created_at=None)


class FakeUserRepo:
    def __init__(self, users=()):
        self.users = {str(u.id): u for u in users}
        self.saved = []

    async def list(self):
        return sorted(self.users.values(), key=lambda u: u.email)

    async def get_by_id(self, user_id):
        return self.users.get(str(user_id))

    async def get_by_email(self, email):
        return next((u for u in self.users.values() if u.email == email), None)

    async def create(self, *, email, name, role, is_verified):
        u = _user(str(uuid.uuid4()), email, role, name=name)
        u.is_verified = is_verified
        self.users[str(u.id)] = u
        return u

    async def save(self, user):
        self.saved.append(user)
        return user


def _service(*users):
    repo = FakeUserRepo(users)
    return UserService(repo), repo


@pytest.mark.asyncio
async def test_list_mengembalikan_semua_user():
    svc, _ = _service(_user(ADMIN_ID, "a@x.com", "admin"), _user(PPIC_ID, "p@x.com", "ppic"))
    assert [u.email for u in await svc.list()] == ["a@x.com", "p@x.com"]


@pytest.mark.asyncio
async def test_create_profil_terverifikasi_dan_email_dinormalisasi():
    svc, repo = _service()
    user = await svc.create(UserCreate(email="Budi@Corp.COM", name=" Budi ", role="purchasing"))

    assert user.email == "budi@corp.com"
    assert user.name == "Budi"
    assert user.role == "purchasing"
    assert user.is_verified is True
    assert await repo.get_by_email("budi@corp.com") is user


@pytest.mark.asyncio
async def test_create_email_sudah_ada_409():
    svc, _ = _service(_user(PPIC_ID, "p@x.com", "ppic"))
    with pytest.raises(UserEmailExistsError):
        await svc.create(UserCreate(email="P@x.com", name="Lagi", role="viewer"))


def test_role_tidak_valid_ditolak_schema():
    with pytest.raises(ValueError):
        UserCreate(email="a@x.com", name="A", role="superuser")


@pytest.mark.asyncio
async def test_update_role_dan_status_user_lain():
    svc, repo = _service(_user(ADMIN_ID, "a@x.com", "admin"), _user(PPIC_ID, "p@x.com", "ppic"))
    user = await svc.update(ADMIN_ID, PPIC_ID, UserUpdate(role="viewer", is_active=False, name="Baru"))

    assert (user.role, user.is_active, user.name) == ("viewer", False, "Baru")
    assert repo.saved == [user]


@pytest.mark.asyncio
async def test_update_user_tidak_ada_404():
    svc, _ = _service(_user(ADMIN_ID, "a@x.com", "admin"))
    with pytest.raises(UserNotFoundError):
        await svc.update(ADMIN_ID, PPIC_ID, UserUpdate(role="viewer"))


@pytest.mark.asyncio
async def test_update_id_bukan_uuid_404():
    svc, _ = _service(_user(ADMIN_ID, "a@x.com", "admin"))
    with pytest.raises(UserNotFoundError):
        await svc.update(ADMIN_ID, "bukan-uuid", UserUpdate(role="viewer"))


@pytest.mark.asyncio
@pytest.mark.parametrize("payload", [UserUpdate(role="ppic"), UserUpdate(is_active=False)])
async def test_admin_tidak_bisa_menurunkan_atau_menonaktifkan_diri_sendiri(payload):
    svc, repo = _service(_user(ADMIN_ID, "a@x.com", "admin"))
    with pytest.raises(UserSelfLockoutError):
        await svc.update(ADMIN_ID, ADMIN_ID, payload)
    assert repo.saved == []


@pytest.mark.asyncio
async def test_admin_boleh_ganti_nama_sendiri():
    svc, _ = _service(_user(ADMIN_ID, "a@x.com", "admin"))
    user = await svc.update(ADMIN_ID, ADMIN_ID, UserUpdate(name="Admin Baru", role="admin", is_active=True))
    assert user.name == "Admin Baru"
