"""
Seed user demo untuk development.

    python -m app.scripts.seed_dev_users

Membuat satu user per role (admin/ppic/purchasing/viewer) di tabel `users`,
semuanya `is_verified=True`. Idempoten: email yang sudah ada dilewati, tidak
ditimpa — jadi aman dijalankan berulang.

Login pakai password bersama DEV_AUTH_PASSWORD (default `demo1234`), yang hanya
berlaku kalau ENVIRONMENT=development + DEV_AUTH_ENABLED=true. Lihat
app/services/dev_auth.py untuk guard-nya.

Skrip ini menolak jalan di luar ENVIRONMENT=development supaya tidak ada akun
demo yang menyelinap ke staging/production.
"""
import asyncio
import sys
from dataclasses import dataclass
from typing import Protocol

from app.config import get_settings
from app.db.session import get_sessionmaker
from app.repositories.user_repository import SqlUserRepository
from app.services.dev_auth import DEV_ENVIRONMENT

__all__ = ["DEMO_USERS", "DemoUser", "seed_users", "run"]


@dataclass(frozen=True)
class DemoUser:
    email: str
    name: str
    role: str


# Satu akun per role supaya RBAC (FR-8.2) bisa dicoba tanpa bikin user manual.
DEMO_USERS: tuple[DemoUser, ...] = (
    DemoUser("admin@forecastiq.dev", "Demo Admin", "admin"),
    DemoUser("ppic@forecastiq.dev", "Demo PPIC", "ppic"),
    DemoUser("purchasing@forecastiq.dev", "Demo Purchasing", "purchasing"),
    DemoUser("viewer@forecastiq.dev", "Demo Viewer", "viewer"),
)


class _UserRepository(Protocol):
    async def get_by_email(self, email: str): ...
    async def create(self, *, email: str, name: str, role: str, is_verified: bool): ...


async def seed_users(users: _UserRepository) -> tuple[list[str], list[str]]:
    """Buat user demo yang belum ada. Return (email dibuat, email dilewati)."""
    created: list[str] = []
    skipped: list[str] = []
    for spec in DEMO_USERS:
        if await users.get_by_email(spec.email) is not None:
            skipped.append(spec.email)
            continue
        await users.create(email=spec.email, name=spec.name, role=spec.role, is_verified=True)
        created.append(spec.email)
    return created, skipped


async def run() -> int:
    settings = get_settings()
    if settings.ENVIRONMENT != DEV_ENVIRONMENT:
        print(
            f"Dibatalkan: ENVIRONMENT={settings.ENVIRONMENT!r}, user demo hanya untuk "
            f"{DEV_ENVIRONMENT!r}.",
            file=sys.stderr,
        )
        return 1

    async with get_sessionmaker()() as session:
        created, skipped = await seed_users(SqlUserRepository(session))
        await session.commit()

    for email in created:
        print(f"  dibuat   {email}")
    for email in skipped:
        print(f"  dilewati {email} (sudah ada)")

    if not settings.DEV_AUTH_ENABLED:
        print(
            "\nCatatan: DEV_AUTH_ENABLED belum true — login lokal masih memakai Supabase Auth.\n"
            "Set DEV_AUTH_ENABLED=true di backend/.env lalu restart backend.",
            file=sys.stderr,
        )
    else:
        print(f"\nPassword semua user demo: {settings.DEV_AUTH_PASSWORD}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run()))
