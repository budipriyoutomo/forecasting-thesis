"""
Authenticator — verifikasi kredensial ke Supabase Auth (GoTrue).

Kontrak: `authenticate(email, password) -> Identity`, raise InvalidCredentialsError
kalau gagal. Backend tetap stateless (AGENTS.md §10 #10) — password tidak pernah
disimpan/di-log di sini; hanya diteruskan ke Supabase.

Untuk MVP, kalau SUPABASE_URL belum dikonfigurasi, authenticate raise error jelas
(bukan diam-diam meloloskan). Di test, authenticator ini di-mock penuh.
"""
from dataclasses import dataclass

import httpx

from app.config import get_settings
from app.utils.exceptions import AppError, InvalidCredentialsError


@dataclass
class Identity:
    """Identitas hasil verifikasi kredensial (dari Supabase Auth)."""

    id: str
    email: str


class AuthProviderUnavailableError(AppError):
    status_code = 503
    code = "AUTH_INVALID_CREDENTIALS"


class SupabaseAuthenticator:
    async def authenticate(self, email: str, password: str) -> Identity:
        settings = get_settings()
        if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
            raise AuthProviderUnavailableError("Supabase Auth belum dikonfigurasi (SUPABASE_URL/SUPABASE_KEY).")

        url = f"{settings.SUPABASE_URL.rstrip('/')}/auth/v1/token"
        try:
            async with httpx.AsyncClient(timeout=10.0) as http:
                resp = await http.post(
                    url,
                    params={"grant_type": "password"},
                    headers={"apikey": settings.SUPABASE_KEY, "Content-Type": "application/json"},
                    json={"email": email, "password": password},
                )
        except httpx.HTTPError as exc:
            raise AuthProviderUnavailableError("Tidak bisa menghubungi Supabase Auth.") from exc

        if resp.status_code != 200:
            raise InvalidCredentialsError("Email atau password salah.")

        data = resp.json()
        user = data.get("user") or {}
        user_id = user.get("id")
        if not user_id:
            raise InvalidCredentialsError("Respons Supabase Auth tidak berisi user id.")
        return Identity(id=str(user_id), email=user.get("email", email))
