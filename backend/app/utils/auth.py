"""
JWT helpers — implementasi minimal untuk Fase 0/scaffold.

Fase 1 (lihat docs/TASK_BREAKDOWN.md) akan mengganti/menambah integrasi
penuh dengan Supabase Auth. Untuk sekarang, modul ini cukup untuk
mendemonstrasikan pola auth-required endpoint dan test 401 sesuai
AGENTS.md §3 (test wajib: auth failure).
"""
from datetime import datetime, timedelta, timezone

import jwt

from app.config import get_settings

settings = get_settings()


def create_access_token(user_id: str, role: str = "ppic") -> str:
    payload = {
        "sub": user_id,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(hours=settings.JWT_EXPIRE_HOURS),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """Raises jwt.ExpiredSignatureError / jwt.InvalidTokenError on failure."""
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
