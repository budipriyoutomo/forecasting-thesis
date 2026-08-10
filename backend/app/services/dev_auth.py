"""
DevAuthenticator — verifikasi kredensial lokal, KHUSUS development.

Kenapa ada: login normal butuh Supabase Auth (app/services/supabase_auth.py).
Di mesin dev tanpa SUPABASE_URL/SUPABASE_KEY, login mustahil, jadi UI tidak bisa
dicoba sama sekali. Authenticator ini menggantinya dengan satu password bersama
untuk user demo hasil `scripts/seed_dev_users.py`.

Ini jalur bypass, jadi dijaga berlapis:
  1. Hanya dipakai kalau ENVIRONMENT == "development" DAN DEV_AUTH_ENABLED=true.
  2. build_authenticator() mengabaikan flag di environment lain — kalau .env dev
     ikut ter-deploy, yang aktif tetap Supabase.
  3. Konstruktor raise (bukan diam-diam meloloskan) kalau guard dilanggar.
  4. Password wajib di-set eksplisit; kosong = ditolak.

Authenticator ini TIDAK memutuskan siapa yang boleh masuk — user tetap harus ada
di tabel `users` dan is_verified, dicek AuthService setelah ini.
"""
import uuid

from app.config import Settings, get_settings
from app.services.supabase_auth import Identity, SupabaseAuthenticator
from app.utils.exceptions import AppError, InvalidCredentialsError

__all__ = ["DevAuthenticator", "DevAuthNotAllowedError", "build_authenticator"]

DEV_ENVIRONMENT = "development"

# Namespace tetap supaya id yang diturunkan dari email stabil antar-restart.
_DEV_ID_NAMESPACE = uuid.UUID("9f1d5b6e-0c2a-4f7d-9c3e-2b6a1d0e4f88")


class DevAuthNotAllowedError(AppError):
    status_code = 500
    code = "AUTH_INVALID_CREDENTIALS"


class DevAuthenticator:
    """Meloloskan siapa pun yang tahu DEV_AUTH_PASSWORD. Development saja."""

    def __init__(self, settings: Settings | None = None):
        settings = settings or get_settings()
        if settings.ENVIRONMENT != DEV_ENVIRONMENT:
            raise DevAuthNotAllowedError(
                f"DevAuthenticator hanya boleh di ENVIRONMENT={DEV_ENVIRONMENT}, "
                f"bukan '{settings.ENVIRONMENT}'."
            )
        if not settings.DEV_AUTH_PASSWORD:
            raise DevAuthNotAllowedError("DEV_AUTH_PASSWORD kosong — dev login dinonaktifkan.")
        self._password = settings.DEV_AUTH_PASSWORD

    async def authenticate(self, email: str, password: str) -> Identity:
        if password != self._password:
            raise InvalidCredentialsError("Email atau password salah.")
        # Id di sini tidak dipakai untuk otorisasi — AuthService memakai id dari
        # tabel `users`. Diturunkan dari email semata agar deterministik.
        return Identity(id=str(uuid.uuid5(_DEV_ID_NAMESPACE, email)), email=email)


def build_authenticator(settings: Settings | None = None):
    """Pilih authenticator sesuai environment. Default selalu Supabase."""
    settings = settings or get_settings()
    if settings.ENVIRONMENT == DEV_ENVIRONMENT and settings.DEV_AUTH_ENABLED:
        return DevAuthenticator(settings)
    return SupabaseAuthenticator()
