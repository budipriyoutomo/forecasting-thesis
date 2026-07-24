"""
Titik kumpul semua ORM model untuk Alembic autogenerate.

Di-import hanya oleh `alembic/env.py` (bukan oleh `app.db.base`) supaya tidak
terjadi circular import — model meng-import `Base` dari `app.db.base`, jadi
`base` tidak boleh balik meng-import model. Tambahkan model baru di sini tiap fase.
"""
from app.db.base import Base
from app.models.user import User  # noqa: F401

__all__ = ["Base"]
