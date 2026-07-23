"""
Prophet — BELUM DIIMPLEMENTASIKAN.

Alasan: package `prophet` butuh build cmdstan (kompilasi native code) yang
berat dan lambat untuk di-provision di CI/dev standar. Ditunda sampai benar-
benar dibutuhkan (lihat docs/ARCHITECTURE.md §6.6 dan docs/TASK_BREAKDOWN.md
Fase 4).

PENTING: jangan daftarkan `forecast_prophet` ke MODEL_REGISTRY (registry.py)
sampai fungsi ini benar-benar diimplementasikan dan diuji — auto-selection
tidak boleh pernah mencoba memanggil fungsi yang belum ada.

Saat diimplementasikan nanti, ikuti kontrak yang sama seperti engine lain:

    def forecast_prophet(df: pd.DataFrame, horizon: int) -> EngineResult: ...

lihat ets_engine.py / arima_engine.py sebagai contoh pola (holdout backtest
untuk MASE, lalu refit di seluruh data, lalu predict `horizon` ke depan).
"""
import pandas as pd

from app.services.forecasting.types import EngineResult


def forecast_prophet(df: pd.DataFrame, horizon: int) -> EngineResult:
    raise NotImplementedError(
        "forecast_prophet belum diimplementasikan — lihat docstring modul ini. "
        "Jangan didaftarkan ke registry.py sebelum ini selesai."
    )
