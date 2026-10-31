"""
Helper bersama untuk menyiapkan time series harian dari data mentah.
Dipakai oleh classification.py dan semua fungsi engine (bukan "metode
forecasting" itu sendiri — jadi tidak melanggar aturan 1-fungsi-1-metode di
AGENTS.md §5, ini murni utilitas pra-pemrosesan yang dipakai bersama).
"""
import pandas as pd


def to_daily_series(df: pd.DataFrame) -> pd.Series:
    """
    Ubah df (kolom `date`, `quantity`) jadi Series harian penuh — tanggal
    tanpa transaksi diisi 0. Dipakai engine legacy v2.0 (ADI/CV², intermittent).
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


def _is_monthly(delta: pd.Timedelta) -> bool:
    return pd.Timedelta(days=28) <= delta <= pd.Timedelta(days=31)


def future_timestamps(last_date, horizon: int, delta: pd.Timedelta) -> list[pd.Timestamp]:
    """`horizon` periode ke depan. Data bulanan (selisih 28–31 hari) melangkah per bulan
    kalender — `last + 31 hari` akan bergeser dari awal/akhir bulan (Fase 11.2b, supaya
    periode forecast sejajar dengan periode variabel eksternal & proyeksi stok)."""
    last = pd.Timestamp(last_date)
    if _is_monthly(delta):
        month_end = last.is_month_end and last.day != 1
        offset = pd.offsets.MonthEnd(1) if month_end else pd.DateOffset(months=1)
        return [last + offset * (i + 1) for i in range(horizon)]
    return [last + delta * (i + 1) for i in range(horizon)]


def future_dates(last_date, horizon: int, delta: pd.Timedelta) -> list[str]:
    """Daftar tanggal (ISO string) `horizon` periode ke depan."""
    return [str(ts.date()) for ts in future_timestamps(last_date, horizon, delta)]


def cap_outliers_iqr(series: pd.Series, k: float = 1.5) -> tuple[pd.Series, int]:
    """Winsorize metode IQR: nilai di luar [Q1 − k·IQR, Q3 + k·IQR] di-cap ke batasnya.
    Return (series ter-cap, jumlah titik yang diubah). Dipakai ML bila `ml_winsorize`."""
    q1, q3 = series.quantile(0.25), series.quantile(0.75)
    iqr = q3 - q1
    lower, upper = q1 - k * iqr, q3 + k * iqr
    capped = series.clip(lower=lower, upper=upper)
    return capped, int((capped != series).sum())
