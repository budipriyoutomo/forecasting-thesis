"""
Titik kumpul semua ORM model untuk Alembic autogenerate.

Di-import hanya oleh `alembic/env.py` (bukan oleh `app.db.base`) supaya tidak
terjadi circular import — model meng-import `Base` dari `app.db.base`, jadi
`base` tidak boleh balik meng-import model. Tambahkan model baru di sini tiap fase.
"""
from app.db.base import Base
from app.models.consumption_history import ConsumptionHistory  # noqa: F401
from app.models.forecast_result import ForecastResult  # noqa: F401
from app.models.forecast_run import ForecastRun  # noqa: F401
from app.models.material import Material  # noqa: F401
from app.models.override import Override  # noqa: F401
from app.models.reorder_recommendation import ReorderRecommendation  # noqa: F401
from app.models.upload_session import UploadSession  # noqa: F401
from app.models.user import User  # noqa: F401

__all__ = ["Base"]
