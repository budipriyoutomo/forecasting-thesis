"""CR v3.4 §4.1 — periode dinormalisasi ke awal bulan (sumber tunggal untuk demand & exog)."""
from datetime import date, datetime

import pandas as pd
import pytest

from app.services.forecasting.preprocessing import normalize_period


@pytest.mark.parametrize(
    "value",
    ["2024-01-24", "2024-01-01", "2024-01-31 13:45", date(2024, 1, 24), datetime(2024, 1, 24, 8), pd.Timestamp("2024-01-24")],
)
def test_normalize_period_ke_awal_bulan(value):
    assert normalize_period(value) == date(2024, 1, 1)


@pytest.mark.parametrize("value", [None, "", "bukan-tanggal", float("nan")])
def test_normalize_period_tidak_valid_raise_value_error(value):
    with pytest.raises(ValueError):
        normalize_period(value)
