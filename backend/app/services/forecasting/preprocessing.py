"""
Helper bersama untuk menyiapkan time series dari `consumption_history` mentah.
Dipakai oleh classification.py dan semua fungsi engine (bukan "metode
forecasting" itu sendiri — jadi tidak melanggar aturan 1-fungsi-1-metode di
AGENTS.md §5, ini murni utilitas pra-pemrosesan yang dipakai bersama).
"""
import pandas as pd


def to_daily_series(df: pd.DataFrame) -> pd.Series:
    """
    Ubah df (kolom `date`, `quantity`) jadi Series harian penuh — tanggal
    tanpa transaksi diisi 0. Dibutuhkan untuk ADI/CV² (classification.py)
    dan sebagai input rolling-origin backtest tiap engine.
    """
    working = df.copy()
    working["date"] = pd.to_datetime(working["date"])
    daily = working.groupby("date")["quantity"].sum()
    full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    return daily.reindex(full_range, fill_value=0)
