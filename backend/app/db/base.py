"""
Declarative base untuk semua ORM model (docs/ARCHITECTURE.md §4).

Model per tabel ditambahkan mulai Fase 1/2 di `app/models/` dan WAJIB di-import
di sini supaya ikut terbaca `alembic revision --autogenerate`.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Import model di bawah ini seiring fase berjalan (mis. `from app.models.user import User  # noqa: F401`).
# Tanpa import, tabelnya tidak ikut ke autogenerate migration.
