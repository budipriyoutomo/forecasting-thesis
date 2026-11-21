"""
UserService (CR v3.7, 21 Nov 2026) — User Management khusus admin (PRD FR-8.4).

- Profil + role disimpan di tabel `users`; password tetap di Supabase Auth. Login cocok lewat
  email (AuthService), jadi admin cukup mendaftarkan email yang sama dengan akun Supabase-nya.
- Email dinormalisasi lowercase (Supabase juga menyimpan lowercase).
- Profil baru langsung `is_verified=True`: admin yang mendaftarkan = verifikasi.
- User tidak dihapus (forecast run / override menyimpan FK) — dinonaktifkan via `is_active`.
- Pengaman: admin tidak bisa menurunkan role / menonaktifkan dirinya sendiri. Karena aktor
  selalu admin aktif, aturan ini sekaligus menjamin minimal satu admin tersisa.
- Perubahan role/status berlaku saat login berikutnya (role dibawa JWT, maks JWT_EXPIRE_HOURS).
"""
# Kelas punya method `list` → tanpa ini anotasi list[...] rusak di Python 3.11 (VPS).
from __future__ import annotations

import uuid

from app.utils.exceptions import UserEmailExistsError, UserNotFoundError, UserSelfLockoutError


class UserService:
    def __init__(self, repo):
        self._repo = repo

    async def list(self):
        return await self._repo.list()

    async def create(self, payload):
        email = str(payload.email).strip().lower()
        if await self._repo.get_by_email(email) is not None:
            raise UserEmailExistsError(f"Email '{email}' sudah terdaftar.")
        return await self._repo.create(email=email, name=payload.name, role=payload.role, is_verified=True)

    async def update(self, actor_id: str, user_id: str, payload):
        try:
            uuid.UUID(str(user_id))
        except ValueError as exc:
            raise UserNotFoundError("User tidak ditemukan.") from exc
        user = await self._repo.get_by_id(user_id)
        if user is None:
            raise UserNotFoundError("User tidak ditemukan.")

        changes = payload.model_dump(exclude_unset=True, exclude_none=True)
        if str(user.id) == str(actor_id):
            if changes.get("role", user.role) != user.role or changes.get("is_active", True) is False:
                raise UserSelfLockoutError(
                    "Anda tidak bisa menurunkan role atau menonaktifkan akun Anda sendiri. "
                    "Minta admin lain melakukannya."
                )
        for field, value in changes.items():
            setattr(user, field, value)
        return await self._repo.save(user)
