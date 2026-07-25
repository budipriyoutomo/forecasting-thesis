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
    tanpa transaksi diisi 0. Dipakai engine legacy v2.0 (ADI/CV², intermittent)
    dan reorder demand_stats.
    """
    working = df.copy()
    working["date"] = pd.to_datetime(working["date"])
    daily = working.groupby("date")["quantity"].sum()
    full_range = pd.date_range(daily.index.min(), daily.index.max(), freq="D")
    return daily.reindex(full_range, fill_value=0)


def to_period_series(df: pd.DataFrame) -> pd.Series:
    """
    Ubah df (kolom `date`, `quantity`) jadi Series terurut per periode APA ADANYA —
    TIDAK di-reindex/di-fill (beda dari to_daily_series). Data thesis bulanan: satu
    titik per bulan harus tetap satu titik, bukan diledakkan jadi ratusan hari nol.
    Dipakai seluruh engine v3.0 (moving_average, exponential_smoothing, RF, XGB, LSTM).
    """
    working = df.copy()
    working["date"] = pd.to_datetime(working["date"])
    series = working.groupby("date")["quantity"].sum().sort_index()
    return series


def infer_period_delta(index: pd.DatetimeIndex) -> pd.Timedelta:
    """Selisih periode dominan (median) — untuk melangkahkan tanggal forecast ke depan."""
    if len(index) < 2:
        return pd.Timedelta(days=1)
    deltas = pd.Series(index[1:]) - pd.Series(index[:-1].to_numpy())
    return deltas.median()


def future_dates(last_date, horizon: int, delta: pd.Timedelta) -> list[str]:
    """Daftar tanggal (ISO string) `horizon` periode ke depan, langkah = delta."""
    last = pd.Timestamp(last_date)
    return [str((last + delta * (i + 1)).date()) for i in range(horizon)]
