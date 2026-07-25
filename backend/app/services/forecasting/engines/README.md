# Kontrak Forecasting Engine v3.0 — 1 Fungsi per Metode

> Wajib dibaca sebelum menambah atau mengubah file di folder ini (AGENTS.md §5, docs/ARCHITECTURE.md §6.0/§6.4).
>
> **v3.0 (Comparative Selection):** tidak ada lagi klasifikasi kuadran ADI/CV². Seluruh metode aktif
> dibandingkan langsung via backtest, metrik ranking terendah menang (`FORECAST_RANKING_METRIC`).
> Engine legacy v2.0 (ETS/ARIMA/LightGBM/Croston) dipindah ke `legacy/` — nonaktif, jangan dihapus (larangan #16).

## Kontrak fungsi

Setiap metode forecasting adalah **satu fungsi publik** per file, bukan class:

```python
def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult:
    """
    df: kolom wajib `date` (datetime-like) dan `quantity` (numeric), untuk SATU produk/SKU.
    horizon: jumlah periode ke depan yang diminta.

    Fungsi ini SELF-CONTAINED:
      1. `to_period_series(df)` — deret per periode APA ADANYA (TIDAK di-fill nol; data bulanan)
      2. Split holdout (`metrics.train_test_split_series`)
      3. Fit di train, prediksi holdout, hitung MAD/MFE/MSE/MAPE (`evaluation.backtest_metrics`,
         MASE opsional bila `settings.COMPUTE_MASE`)
      4. Fit ulang di SELURUH data, predict `horizon` ke depan (dgn lower/upper via `_common.build_points`)
      5. Generate `explanation` bahasa natural (sebut metode + MAPE backtest)

    Return: EngineResult(forecast, explanation, mad, mfe, mse, mape, mase)
    """
```

`ForecastPoint` & `EngineResult` di `../types.py`. Helper bersama (bukan "metode", boleh dipakai semua engine):

- `../preprocessing.py` → `to_period_series(df)`, `infer_period_delta()`, `future_dates()`
- `../evaluation.py` → `mad/mfe/mse/mape`, `backtest_metrics()`
- `../metrics.py` → `train_test_split_series()`, `mean_absolute_scaled_error()` (MASE opsional)
- `_common.py` → `build_points()`, `resid_std()`  ·  `_ml.py` → fitur lag+kalender & forecast rekursif (RF/XGB)

## Cara menambah engine baru

1. Buat `<nama>_engine.py`, tulis **satu** fungsi `forecast_<nama>(df, horizon) -> EngineResult`.
2. Tulis test dulu (`tests/unit/test_<nama>_engine.py`) — TDD wajib (AGENTS.md §3).
3. Daftarkan di `../registry.py` → `MODEL_REGISTRY["<nama>"] = forecast_<nama>`.
4. Aktifkan lewat env `FORECAST_ENGINES_ENABLED` (tak ada lagi pemetaan kuadran).
5. **Jangan** ubah `forecast_service.py`, endpoint, atau engine lain — cukup tambah kode baru.

## Status & minimum data per metode (aktif v3.0)

| Metode | File | Fungsi | Minimum data | Catatan |
|---|---|---|---|---|
| Moving Average | `moving_average_engine.py` | `forecast_moving_average` | `BACKTEST_MIN_PERIODS` (12) | window `MOVING_AVERAGE_WINDOW` (3) |
| Exponential Smoothing | `exponential_smoothing_engine.py` | `forecast_exponential_smoothing` | 12 | SES manual, α tuned grid 0.1–0.9 |
| Random Forest | `random_forest_engine.py` | `forecast_random_forest` | 12 | fitur lag [1,12] + bulan, rekursif |
| XGBoost | `xgboost_engine.py` | `forecast_xgboost` | 12 | fitur lag [1,2,12] + bulan, rekursif |
| LSTM | `lstm_engine.py` | `forecast_lstm` | `LSTM_MIN_PERIODS` (24) | TF lazy-import; auto-excluded bila TF absen |

> Legacy (nonaktif, di `legacy/`): `ets_engine.py`, `arima_engine.py`, `lightgbm_engine.py`, `croston_engine.py`, `prophet_engine.py` (TODO). Lihat docs/ARCHITECTURE.md §6.9.
>
> Update tabel ini setiap menambah/mengubah engine — jangan biarkan basi.
