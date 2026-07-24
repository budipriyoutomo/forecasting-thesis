"""
AuthService — orkestrasi login & profil (Fase 1, FR-8).

Alur login:
  1. Verifikasi kredensial ke authenticator (Supabase Auth) → Identity.
  2. Ambil profil user dari tabel `users` (role, is_verified).
  3. Tolak kalau profil tidak ada (InvalidCredentials) atau belum verified.
  4. Terbitkan JWT backend sendiri (app/utils/auth.py) berisi sub + role,
     dipakai semua endpoint lain lewat get_current_user (AGENTS.md pola existing).

Kredensial (password) tidak pernah disimpan/di-log di sini.
"""
from typing import Protocol

from app.services.supabase_auth import Identity
from app.utils.auth import create_access_token
from app.utils.exceptions import AuthEmailNotVerifiedError, InvalidCredentialsError

__all__ = ["AuthService", "Identity"]


class _Authenticator(Protocol):
    async def authenticate(self, email: str, password: str) -> Identity: ...


class _UserRepository(Protocol):
    async def get_by_email(self, email: str): ...
    async def get_by_id(self, user_id: str): ...


class AuthService:
    def __init__(self, users: _UserRepository, authenticator: _Authenticator):
        self._users = users
        self._authenticator = authenticator

    async def login(self, email: str, password: str):
        # Raise InvalidCredentialsError kalau kredensial salah (dari authenticator).
        await self._authenticator.authenticate(email, password)

        user = await self._users.get_by_email(email)
        if user is None:
            # Kredensial Supabase valid tapi belum ada profil/role di sistem kita.
            raise InvalidCredentialsError("Email atau password salah.")
        if not user.is_verified:
            raise AuthEmailNotVerifiedError("Email belum terverifikasi.")

        token = create_access_token(str(user.id), user.role)
        return token, user

    async def get_profile(self, user_id: str):
        user = await self._users.get_by_id(user_id)
        if user is None:
            raise InvalidCredentialsError("User tidak ditemukan.")
        return user
