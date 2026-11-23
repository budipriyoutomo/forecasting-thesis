"""Fase 3 v3.0 — parsing CSV demand produk (3 seri paralel)."""
from decimal import Decimal

import pytest

from app.services import data_ingestion_service as ing
from app.utils.exceptions import InsufficientDataError, UploadInvalidFormatError


def _csv(header: str, rows: list[str]) -> bytes:
    return ("\n".join([header, *rows])).encode("utf-8")


def test_extract_demand_rows_lengkap():
    content = _csv(
        "product_code,period,forecast_existing,planning,actual",
        ["SKU-1,2026-01-01,90,95,100", "SKU-1,2026-02-01,,,110"],
    )
    rows = ing.extract_demand_rows(content)
    assert len(rows) == 2
    assert rows[0]["forecast_existing"] == Decimal("90")
    assert rows[0]["actual"] == Decimal("100")
    # kolom opsional kosong → None, actual tetap terisi
    assert rows[1]["forecast_existing"] is None
    assert rows[1]["planning"] is None
    assert rows[1]["actual"] == Decimal("110")


def test_period_alias_date_diterima():
    content = _csv("product_code,date,actual", ["SKU-1,2026-03-01,50"])
    rows = ing.extract_demand_rows(content)
    assert rows[0]["period"].isoformat() == "2026-03-01"


def test_extract_demand_rows_normalisasi_periode():
    """CR v3.4 §4.1 — tanggal 24 (format Excel thesis) disimpan sebagai awal bulan."""
    content = _csv("product_code,period,actual", ["SKU-1,2024-01-24,100", "SKU-1,2024-02-29,110"])
    rows = ing.extract_demand_rows(content)
    assert [r["period"].isoformat() for r in rows] == ["2024-01-01", "2024-02-01"]


def test_baris_actual_kosong_dilewati():
    content = _csv("product_code,period,actual", ["SKU-1,2026-01-01,", "SKU-1,2026-02-01,120"])
    rows = ing.extract_demand_rows(content)
    assert [str(r["actual"]) for r in rows] == ["120"]


# ── 23 Nov 2026 — baris rusak dulu dibuang diam-diam (upload "sukses" padahal data hilang)
# atau lolos lalu crash di DB (500). Kini seluruh file ditolak dengan nomor baris, sama
# seperti importer stok ERP / pemakaian material.

_H = "product_code,period,forecast_existing,planning,actual"


@pytest.mark.parametrize(
    "row,match",
    [
        ("SKU-1,2026-02-01,1,1,abc", "Baris 3: 'actual' bukan angka valid"),
        ("SKU-1,2026-02-01,1,1,Infinity", "Baris 3: 'actual' bukan angka valid"),
        ("SKU-1,2026-02-01,1,1,1e20", "Baris 3: 'actual' terlalu besar"),
        ("SKU-1,2026-02-01,1,1,-5", "Baris 3: 'actual' tidak boleh negatif"),
        ("SKU-1,2026-02-01,x,1,5", "Baris 3: 'forecast_existing' bukan angka valid"),
        ("SKU-1,2026-02-01,1,-1,5", "Baris 3: 'planning' tidak boleh negatif"),
        ("SKU-1,,1,1,5", "Baris 3: 'period' wajib diisi"),
        ("SKU-1,besok,1,1,5", "Baris 3: 'period' bukan tanggal valid"),
        # dd/mm vs mm/dd ambigu — dulu 05/10/2025 diam-diam jadi Mei.
        ("SKU-1,05/10/2025,1,1,5", "Baris 3: 'period'.*YYYY-MM-DD"),
        (",2026-02-01,1,1,5", "Baris 3: 'product_code' wajib diisi"),
    ],
)
def test_baris_tidak_valid_menolak_file(row, match):
    content = _csv(_H, ["SKU-1,2026-01-01,1,1,5", row])
    with pytest.raises(UploadInvalidFormatError, match=match):
        ing.extract_demand_rows(content)


def test_validate_baris_rusak_tidak_dihitung_lolos():
    rows = [f"SKU-1,2025-{m:02d}-01,1,1,{m}" for m in range(1, 12)] + ["SKU-1,xx,1,1,1"]
    with pytest.raises(UploadInvalidFormatError, match="Baris 13"):
        ing.parse_and_validate_csv("f.csv", _csv(_H, rows))


def test_validate_n_rows_hanya_baris_tersimpan_dan_actual_kosong_dilaporkan():
    rows = [f"SKU-1,2025-{m:02d}-01,1,1,{m}" for m in range(1, 13)] + ["SKU-1,2026-01-01,1,1,", ",,,,", ",,,,"]
    summary = ing.parse_and_validate_csv("f.csv", _csv(_H, rows))
    assert summary["n_rows"] == 12
    assert summary["warnings"] == ["1 baris dengan 'actual' kosong dilewati (baris 14)."]


def test_validate_minimal_baris_dihitung_dari_baris_valid():
    # 12 baris di file, tapi 3 actual kosong → hanya 9 baris valid (< UPLOAD_MIN_ROWS 10).
    rows = [f"SKU-1,2025-{m:02d}-01,1,1,{m if m <= 9 else ''}" for m in range(1, 13)]
    with pytest.raises(InsufficientDataError, match="9 baris"):
        ing.parse_and_validate_csv("f.csv", _csv(_H, rows))


def test_duplikat_produk_tanggal_diterima_tapi_dilaporkan():
    # Bisa sah (mis. per channel) — dijumlahkan saat forecast seperti CR v3.4, tapi tidak diam-diam.
    rows = [f"SKU-1,2025-{m:02d}-01,1,1,{m}" for m in range(1, 13)] + ["SKU-1,2025-01-01,1,1,7"]
    summary = ing.parse_and_validate_csv("f.csv", _csv(_H, rows))
    assert summary["n_rows"] == 13
    assert summary["warnings"] == [
        "1 baris punya produk + tanggal yang sama dengan baris lain (mis. baris 14 = baris 2: SKU-1 2025-01-01) "
        "— nilainya dijumlahkan saat forecast. Hapus bila tidak disengaja (mis. file terunggah dua kali)."
    ]


def test_csv_excel_indonesia_titik_koma_desimal_koma_dan_kode_angka():
    content = "product_code;period;forecast_existing;planning;actual\n001;2026-01-01;90,5;95;1.234,5\n".encode()
    rows = ing.extract_demand_rows(content)
    assert rows[0]["product_code"] == "001"  # dulu terbaca angka → "1"
    assert rows[0]["forecast_existing"] == Decimal("90.5")
    assert rows[0]["actual"] == Decimal("1234.5")


def test_bom_utf8_dan_format_bulan_tetap_diterima():
    content = "\ufeffproduct_code,period,actual\nSKU-1,Jan-2024,5\nSKU-1,2024-02-24 00:00:00,6\n".encode()
    rows = ing.extract_demand_rows(content)
    assert [r["period"].isoformat() for r in rows] == ["2024-01-01", "2024-02-01"]


def test_validate_kolom_actual_hilang():
    content = _csv("product_code,period", [f"SKU-1,2026-01-{i:02d}" for i in range(1, 13)])
    with pytest.raises(UploadInvalidFormatError, match="actual"):
        ing.parse_and_validate_csv("f.csv", content)


def test_validate_n_products_detected():
    content = _csv(
        "product_code,period,actual",
        [f"SKU-{i % 2},2026-01-{(i % 28) + 1:02d},{10 + i}" for i in range(12)],
    )
    summary = ing.parse_and_validate_csv("f.csv", content)
    assert summary["n_products_detected"] == 2
    assert summary["n_rows"] == 12


def test_validate_insufficient_rows():
    content = _csv("product_code,period,actual", ["SKU-1,2026-01-01,10"])
    with pytest.raises(InsufficientDataError):
        ing.parse_and_validate_csv("f.csv", content)


# ── CR v3.4 §4.1 — normalisasi periode demand tidak boleh diam-diam ──


def test_extract_demand_rows_simpan_tanggal_asli():
    rows = ing.extract_demand_rows(_csv("product_code,period,actual", ["SKU-1,2024-01-24,100"]))
    assert rows[0]["period_original"].isoformat() == "2024-01-24"


def test_demand_period_warnings_normalisasi_dan_bulan_ganda():
    content = _csv(
        "product_code,period,actual",
        ["SKU-1,2024-01-24,100", "SKU-1,2024-02-01,90", "SKU-1,2024-01-25,80", "SKU-2,2024-01-01,5"],
    )
    warnings = ing.demand_period_warnings(ing.extract_demand_rows(content))
    assert warnings == [
        "2 baris: periode digeser ke awal bulan (mis. 2024-01-24 → 2024-01-01).",
        (
            "1 produk-bulan punya lebih dari satu tanggal (mis. SKU-1 2024-01: 2024-01-24, 2024-01-25) — "
            "nilainya dijumlahkan saat forecast. Cek format tanggal: 'Jan-24' bisa terbaca 24-Jan tahun berjalan."
        ),
    ]


def test_demand_period_warnings_data_rapi_kosong():
    content = _csv("product_code,period,actual", ["SKU-1,2024-01-01,100", "SKU-1,2024-02-01,90"])
    assert ing.demand_period_warnings(ing.extract_demand_rows(content)) == []
