# Kontrak Forecasting Engine — 1 Fungsi per Metode

> Wajib dibaca sebelum menambah atau mengubah file di folder ini (AGENTS.md §5, docs/ARCHITECTURE.md §6.0/§6.6).

## Kontrak fungsi

Setiap metode forecasting adalah **satu fungsi publik** per file, bukan class:

```python
def forecast_<method>(df: pd.DataFrame, horizon: int) -> EngineResult:
    """
    df: kolom wajib `date` (datetime-like) dan `quantity` (numeric), untuk SATU material.
    horizon: jumlah periode (hari) ke depan yang diminta.

    Fungsi ini SELF-CONTAINED:
      1. Split holdout dari `df` (pakai `metrics.train_test_split_series`)
      2. Fit di data training, prediksi periode holdout, hitung MASE
         (pakai `metrics.mean_absolute_scaled_error`)
      3. Fit ulang di SELURUH data
      4. Predict `horizon` periode ke depan (dengan lower/upper bound)
      5. Generate `explanation` (bahasa natural, sebut nama metode + alasan + MASE)

    Return: EngineResult(forecast: list[ForecastPoint], mase: float, explanation: str)
    """
```

`ForecastPoint` dan `EngineResult` didefinisikan di `../types.py` — dipakai bersama oleh semua engine, bukan diduplikasi per file.

Helper bersama yang **boleh** dipakai semua engine (bukan "metode" itu sendiri, jadi tidak melanggar aturan 1-fungsi-1-metode):
- `../preprocessing.py` → `to_daily_series(df)`
- `../metrics.py` → `mean_absolute_scaled_error()`, `train_test_split_series()`

## Cara menambah engine baru

1. Buat file `<nama>_engine.py` di folder ini, tulis **satu** fungsi `forecast_<nama>(df, horizon) -> EngineResult`.
2. Tulis test dulu (`tests/unit/test_<nama>_engine.py`) sebelum implementasi — TDD wajib (AGENTS.md §3).
3. Daftarkan di `../registry.py` → `MODEL_REGISTRY["<nama>"] = forecast_<nama>`.
4. Tambahkan `<nama>` ke kuadran yang relevan di `registry.filter_candidates()` (lihat docs/ARCHITECTURE.md §6.3 — kuadran mana yang cocok untuk metode ini). Method tetap bisa dipilih **manual** oleh user di luar pemetaan kuadran (lihat §6.8).
5. **Jangan** ubah `forecast_service.py`, endpoint, atau test engine lain yang sudah ada — cukup tambah kode baru.

## Status & minimum data requirement per metode

| Metode | File | Fungsi | Kuadran (auto) | Minimum data | Status |
|---|---|---|---|---|---|
| ETS (Exponential Smoothing) | `ets_engine.py` | `forecast_ets` | smooth | ~10 untuk tren, di bawah itu degrade ke simple smoothing | ✅ Implemented |
| ARIMA | `arima_engine.py` | `forecast_arima` | smooth, intermittent (jika cukup) | ~12 (`BACKTEST_MIN_PERIODS`) | ✅ Implemented |
| Croston/SBA | `croston_engine.py` | `forecast_croston` | intermittent, lumpy | ~12 | ✅ Implemented — wajib ada, lihat docs/RECONCILIATION.md |
| LightGBM | `lightgbm_engine.py` | `forecast_lightgbm` | erratic | ≥30 (butuh lag features + training) | ✅ Implemented |
| Prophet | `prophet_engine.py` | `forecast_prophet` | — | — | ⏳ TODO — belum didaftarkan ke registry, lihat docstring file-nya |

> Update tabel ini setiap kali menambah/mengubah engine — jangan biarkan basi.
