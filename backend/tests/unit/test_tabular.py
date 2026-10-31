"""Fase 11.2b — util baca tabel upload (CSV / Excel) bersama untuk import master/transaksi."""
import io

import pandas as pd
import pytest

from app.utils.exceptions import UploadInvalidFormatError
from app.utils.tabular import read_table


def test_csv_header_dinormalisasi():
    df = read_table("x.csv", b" Variable_Code ,Period,Value\nsuhu,2026-01-01,30\n")
    assert list(df.columns) == ["variable_code", "period", "value"]
    assert df.iloc[0]["value"] == 30


def test_excel():
    buf = io.BytesIO()
    pd.DataFrame({"Code": ["a"], "Qty": [5]}).to_excel(buf, index=False)
    df = read_table("data.xlsx", buf.getvalue())
    assert list(df.columns) == ["code", "qty"]
    assert df.iloc[0]["qty"] == 5


@pytest.mark.parametrize("name,content", [("a.pdf", b"x"), ("a.csv", b""), ("a.xlsx", b"bukan excel")])
def test_tidak_valid(name, content):
    with pytest.raises(UploadInvalidFormatError):
        read_table(name, content)


def test_require_columns():
    from app.utils.tabular import require_columns

    df = read_table("x.csv", b"a,b\n1,2\n")
    require_columns(df, {"a"})
    with pytest.raises(UploadInvalidFormatError, match="c"):
        require_columns(df, {"a", "c"})
