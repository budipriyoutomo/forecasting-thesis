"""
Declarative base untuk semua ORM model (docs/ARCHITECTURE.md §4).

Model per tabel ditambahkan mulai Fase 1/2 di `app/models/` dan WAJIB di-import
di sini supaya ikut terbaca `alembic revision --autogenerate`.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# Model TIDAK di-import di sini (menghindari circular import: model butuh Base).
# Untuk autogenerate, model dikumpulkan di app/db/models_registry.py yang di-import
# oleh alembic/env.py.
