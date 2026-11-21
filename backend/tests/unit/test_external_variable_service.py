"""
Fase 11.2b — master data variabel eksternal (Keputusan #7, docs/REVISI_V2.md §6.1).

Variabel dinamis (kode, nama, tipe numeric/flag, scope global/product) dengan toggle
aktif/nonaktif; nilai per periode di-upload. Hanya variabel AKTIF yang dipakai engine ML.
"""
import io
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from app.schemas.external_variable import ExternalVariableCreate, ExternalVariableUpdate, ExternalVariableValueIn
from app.services.external_variable_service import ExternalVariableService, build_exog
from app.utils.exceptions import (
    ExternalVariableCodeExistsError,
    ExternalVariableNotFoundError,
    UploadInvalidFormatError,
)


class FakeVarRepo:
    def __init__(self, variables=None, values=None):
        self.vars = {str(v.id): v for v in (variables or [])}
        self.values = list(values or [])
        self._n = 0

    async def list(self):
        return sorted(self.vars.values(), key=lambda v: v.code)

    async def list_active(self):
        return [v for v in await self.list() if v.is_active]

    async def get_by_id(self, vid):
        return self.vars.get(str(vid))

    async def get_by_code(self, code):
        return next((v for v in self.vars.values() if v.code == code), None)

    async def add(self, var):
        self._n += 1
        var.id = var.id or f"new{self._n}"
        self.vars[str(var.id)] = var
        return var

    async def save(self, var):
        return var

    async def delete(self, var):
        self.vars.pop(str(var.id))
        self.values = [r for r in self.values if str(r.variable_id) != str(var.id)]

    async def upsert_values(self, rows):
        keys = {(str(r.variable_id), str(r.product_id), r.period) for r in rows}
        self.values = [r for r in self.values if (str(r.variable_id), str(r.product_id), r.period) not in keys]
        self.values.extend(rows)
        return len(rows)

    async def list_values(self, variable_id, product_id=None):
        return [
            r for r in self.values
            if str(r.variable_id) == str(variable_id) and (product_id is None or str(r.product_id) == str(product_id))
        ]

    async def delete_values(self, variable_id):
        before = len(self.values)
        self.values = [r for r in self.values if str(r.variable_id) != str(variable_id)]
        return before - len(self.values)

    async def values_for(self, variable_ids, product_id):
        ids = {str(i) for i in variable_ids}
        return [
            r for r in self.values
            if str(r.variable_id) in ids and (r.product_id is None or str(r.product_id) == str(product_id))
        ]

    async def periods_by_variable(self):
        out = {}
        for r in self.values:
            out.setdefault(str(r.variable_id), set()).add(r.period)
        return out

    async def count_values(self):
        out = {}
        for r in self.values:
            out[str(r.variable_id)] = out.get(str(r.variable_id), 0) + 1
        return out


class FakeDemand:
    def __init__(self, first=None, last=None):
        self._range = (first, last)

    async def period_range(self):
        return self._range


class FakeProducts:
    def __init__(self, products):
        self._by_code = {p.code: p for p in products}
        self._by_id = {str(p.id): p for p in products}

    async def get_by_id(self, product_id):
        return self._by_id.get(str(product_id))

    async def get_by_code(self, code):
        return self._by_code.get(code)


def _var(vid, code, value_type="numeric", scope="global", active=True):
    return SimpleNamespace(
        id=vid, code=code, name=code.title(), value_type=value_type, scope=scope,
        unit=None, description=None, is_active=active,
    )


def _val(vid, period, value, product_id=None):
    return SimpleNamespace(variable_id=vid, product_id=product_id, period=period, value=value)


def _var_factory(**kw):
    return SimpleNamespace(id=None, **kw)


def _val_factory(**kw):
    return SimpleNamespace(**kw)


P1 = SimpleNamespace(id="p1", code="KBYPL 200")


def _svc(variables=None, values=None, demand=None):
    repo = FakeVarRepo(variables, values)
    return ExternalVariableService(
        repo, FakeProducts([P1]), demand=demand, var_factory=_var_factory, value_factory=_val_factory
    ), repo


# ── CRUD ──


@pytest.mark.asyncio
async def test_create_dan_kode_duplikat():
    svc, _ = _svc()
    v = await svc.create(ExternalVariableCreate(code="suhu", name="Suhu", value_type="numeric", unit="°C"))
    assert v.is_active is True and v.scope == "global"

    with pytest.raises(ExternalVariableCodeExistsError):
        await svc.create(ExternalVariableCreate(code="suhu", name="Lagi"))


@pytest.mark.parametrize("code", ["Suhu", "1suhu", "suhu udara", "lag_1", "month", ""])
def test_kode_harus_snake_case_dan_bukan_nama_fitur_bawaan(code):
    with pytest.raises(ValueError):
        ExternalVariableCreate(code=code, name="x")


@pytest.mark.asyncio
async def test_update_toggle_aktif_dan_not_found():
    svc, _ = _svc([_var("v1", "promo", "flag", "product")])
    v = await svc.update("v1", ExternalVariableUpdate(is_active=False))
    assert v.is_active is False

    with pytest.raises(ExternalVariableNotFoundError):
        await svc.update("nope", ExternalVariableUpdate(is_active=True))


@pytest.mark.asyncio
async def test_delete_ikut_menghapus_nilai():
    svc, repo = _svc([_var("v1", "suhu")], [_val("v1", date(2026, 1, 1), 30)])
    await svc.delete("v1")
    assert repo.values == [] and repo.vars == {}


# ── Ubah nilai langsung dari dialog "Ubah" (21 Nov 2026) ──


def _items(*rows):
    return [ExternalVariableValueIn(**r) for r in rows]


@pytest.mark.asyncio
async def test_update_values_menimpa_dan_menambah_periode():
    svc, repo = _svc([_var("v1", "suhu")], [_val("v1", date(2026, 1, 1), 30)])
    n = await svc.update_values(
        "v1", _items({"period": "2026-01-01", "value": 31.5}, {"period": "2026-02-15", "value": 29})
    )
    assert n == 2
    got = {(r.period, r.value) for r in repo.values}
    assert got == {(date(2026, 1, 1), 31.5), (date(2026, 2, 1), 29)}  # periode digeser ke awal bulan


@pytest.mark.asyncio
async def test_update_values_per_produk_wajib_produk_valid():
    svc, repo = _svc([_var("v1", "harga", scope="product")])
    with pytest.raises(UploadInvalidFormatError, match="Produk wajib"):
        await svc.update_values("v1", _items({"period": "2026-01-01", "value": 1}))
    with pytest.raises(UploadInvalidFormatError, match="tidak ditemukan"):
        await svc.update_values("v1", _items({"period": "2026-01-01", "value": 1, "product_id": "zz"}))
    assert await svc.update_values("v1", _items({"period": "2026-01-01", "value": 1, "product_id": "p1"})) == 1
    assert repo.values[0].product_id == "p1"


@pytest.mark.asyncio
async def test_update_values_global_abaikan_produk_dan_flag_harus_0_1():
    svc, repo = _svc([_var("v1", "promo", value_type="flag")])
    with pytest.raises(UploadInvalidFormatError, match="0 atau 1"):
        await svc.update_values("v1", _items({"period": "2026-01-01", "value": 2}))
    assert repo.values == []  # all-or-nothing
    await svc.update_values("v1", _items({"period": "2026-01-01", "value": 1, "product_id": "p1"}))
    assert repo.values[0].product_id is None


@pytest.mark.asyncio
async def test_update_values_variabel_tidak_ada():
    svc, _ = _svc()
    with pytest.raises(ExternalVariableNotFoundError):
        await svc.update_values("x", _items({"period": "2026-01-01", "value": 1}))


# ── Import nilai ──

CSV = (
    "variable_code,period,value,product_code\n"
    "suhu,2026-01-01,30,\n"
    "suhu,2026-02-01,31.5,\n"
    "promo,2026-01-01,1,KBYPL 200\n"
)


@pytest.mark.asyncio
async def test_import_nilai_global_dan_per_produk():
    svc, repo = _svc([_var("v1", "suhu"), _var("v2", "promo", "flag", "product")])
    out = await svc.import_values("nilai.csv", CSV.encode())

    assert out["imported"] == 3
    promo = [r for r in repo.values if r.variable_id == "v2"][0]
    assert promo.product_id == "p1" and float(promo.value) == 1
    assert all(r.product_id is None for r in repo.values if r.variable_id == "v1")


@pytest.mark.asyncio
async def test_import_menimpa_nilai_periode_sama():
    svc, repo = _svc([_var("v1", "suhu")], [_val("v1", date(2026, 1, 1), 99)])
    await svc.import_values("n.csv", b"variable_code,period,value\nsuhu,2026-01-01,30\n")
    assert [float(r.value) for r in repo.values] == [30]


@pytest.mark.asyncio
async def test_import_values_tanggal_24_dinormalisasi_ke_awal_bulan():
    svc, repo = _svc([_var("v1", "suhu")])
    out = await svc.import_values(
        "n.csv", b"variable_code,period,value\nsuhu,2024-01-24,27.2\nsuhu,2024-02-01,28\n"
    )
    assert sorted(r.period for r in repo.values) == [date(2024, 1, 1), date(2024, 2, 1)]
    assert out["normalized"] == 1
    assert out["overwritten"] == 0


@pytest.mark.asyncio
async def test_import_duplikat_bulan_sama_baris_terakhir_menang():
    """Baris ganda dengan tanggal SAMA → baris terakhir menang, hanya satu dikirim ke
    repository (repo asli pakai add_all → unique index bentrok bila dobel)."""
    sent = []
    svc, repo = _svc([_var("v1", "suhu"), _var("v2", "promo", "flag", "product")])
    original = repo.upsert_values

    async def spy(rows):
        sent.extend(rows)
        return await original(rows)

    repo.upsert_values = spy
    out = await svc.import_values(
        "n.csv",
        b"variable_code,period,value,product_code\n"
        b"suhu,2024-01-24,27,\n"
        b"suhu,2024-01-24,27.2,\n"
        b"promo,2024-01-24,0,KBYPL 200\n"
        b"promo,2024-01-24,1,KBYPL 200\n",
    )
    assert len(sent) == 2
    assert float(next(r.value for r in sent if r.variable_id == "v1")) == 27.2
    assert float(next(r.value for r in sent if r.variable_id == "v2")) == 1
    assert (out["imported"], out["normalized"], out["overwritten"]) == (2, 4, 2)


@pytest.mark.asyncio
async def test_import_tanggal_berbeda_di_bulan_sama_ditolak():
    """'Jan-24' yang diketik di sel format d-mmm tersimpan sebagai 24-Jan-<tahun berjalan>:
    Jan 2024/2025/2026 jadi 2026-01-24/25/26. Normalisasi akan melebur 3 tahun jadi satu
    bulan → wajib ditolak, bukan ditimpa diam-diam."""
    svc, repo = _svc([_var("v1", "suhu")])
    body = b"period,suhu\n2026-01-24,27.2\n2026-02-24,27.3\n2026-01-25,26.9\n"
    out = await svc.import_values("lebar.csv", body, dry_run=True)

    assert out["valid"] is False
    assert len(out["errors"]) == 1
    assert out["errors"][0].startswith("Baris 4: periode 2026-01-25 jatuh di bulan yang sama dengan baris 2")
    assert "Jan-24" in out["errors"][0]
    with pytest.raises(UploadInvalidFormatError, match="bulan yang sama"):
        await svc.import_values("lebar.csv", body)
    assert repo.values == []


@pytest.mark.asyncio
async def test_exog_tanggal_24_tetap_terpakai_engine():
    """Integrasi: import tgl 24 → build_exog → usable_exog terhadap periode demand (tgl 1)."""
    from app.services.forecasting.engines._ml import usable_exog

    svc, _ = _svc([_var("v1", "suhu")])
    body = "variable_code,period,value\n" + "".join(
        f"suhu,2024-{m:02d}-24,{26 + m / 10}\n" for m in range(1, 7)
    )
    await svc.import_values("n.csv", body.encode())
    exog = await svc.exog_for_product("p1")
    periods = pd.date_range("2024-01-01", periods=6, freq="MS")

    used, dropped = usable_exog(exog, periods[:4], periods[4:])
    assert dropped == {}
    assert list(used.columns) == ["suhu"]


@pytest.mark.parametrize(
    "body,match",
    [
        ("variable_code,period,value\nhujan,2026-01-01,1\n", "tidak dikenal"),
        ("variable_code,period,value\npromo,2026-01-01,1\n", "product_code wajib"),
        ("variable_code,period,value,product_code\nsuhu,2026-01-01,1,KBYPL 200\n", "global"),
        ("variable_code,period,value,product_code\npromo,2026-01-01,2,KBYPL 200\n", "0 atau 1"),
        ("variable_code,period,value,product_code\npromo,2026-01-01,1,XX\n", "Produk"),
        ("variable_code,period,value\nsuhu,bukan-tanggal,1\n", "period"),
        ("variable_code,period,value\nsuhu,2026-01-01,abc\n", "value"),
        ("variable_code,period\nsuhu,2026-01-01\n", "value"),
        ("variable_code,period,value\n", "tidak berisi"),
    ],
)
@pytest.mark.asyncio
async def test_import_tidak_valid(body, match):
    svc, repo = _svc([_var("v1", "suhu"), _var("v2", "promo", "flag", "product")])
    with pytest.raises(UploadInvalidFormatError, match=match):
        await svc.import_values("n.csv", body.encode())
    assert repo.values == []


# ── Exog untuk engine ──


def test_build_exog_aktif_global_dan_produk():
    variables = [_var("v1", "suhu"), _var("v2", "promo", "flag", "product")]
    values = [
        _val("v1", date(2026, 1, 1), 30), _val("v1", date(2026, 2, 1), 31),
        _val("v2", date(2026, 1, 1), 1, "p1"),
    ]
    exog = build_exog(variables, values)

    assert list(exog.columns) == ["promo", "suhu"]
    assert exog.loc[pd.Timestamp("2026-01-01"), "suhu"] == 30
    assert pd.isna(exog.loc[pd.Timestamp("2026-02-01"), "promo"])


def test_build_exog_kosong():
    assert build_exog([], []) is None


@pytest.mark.asyncio
async def test_exog_for_product_hanya_variabel_aktif():
    svc, _ = _svc(
        [_var("v1", "suhu"), _var("v2", "promo", "flag", "product", active=False)],
        [_val("v1", date(2026, 1, 1), 30), _val("v2", date(2026, 1, 1), 1, "p1")],
    )
    exog = await svc.exog_for_product("p1")
    assert list(exog.columns) == ["suhu"]
    assert await _svc()[0].exog_for_product("p1") is None


# ── Kelengkapan (CR v3.4 §4.2) ──


@pytest.mark.asyncio
async def test_coverage_periode_demand_plus_horizon():
    """Target = bulan pertama..terakhir demand + `horizon` bulan ke depan."""
    months = [date(2024, m, 1) for m in range(1, 6)]
    svc, _ = _svc(
        [_var("v1", "suhu"), _var("v2", "promo", "flag", "product")],
        [_val("v1", d, 27) for d in months[:4]] + [_val("v2", months[0], 1, "p1")],
        demand=FakeDemand(date(2024, 1, 1), date(2024, 3, 1)),
    )
    out = {c["code"]: c for c in await svc.coverage(horizon=2)}

    assert out["suhu"] == {
        "variable_id": "v1", "code": "suhu",
        "first_period": date(2024, 1, 1), "last_period": date(2024, 4, 1),
        "n_expected": 5, "n_filled": 4, "missing_periods": [date(2024, 5, 1)],
    }
    assert out["promo"]["n_filled"] == 1
    assert out["promo"]["missing_periods"] == months[1:]


@pytest.mark.asyncio
async def test_coverage_tanpa_demand_dan_tanpa_nilai():
    svc, _ = _svc([_var("v1", "suhu")], demand=FakeDemand())
    [c] = await svc.coverage(horizon=3)
    assert c["n_expected"] == 0 and c["missing_periods"] == []
    assert c["first_period"] is None and c["last_period"] is None


# ── CR v3.4 §4.3 — import toleran, format lebar, dry-run, template ──


def _xlsx(rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    pd.DataFrame(rows).to_excel(buf, index=False)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_import_long_sel_kosong_dilewati_dan_dilaporkan():
    svc, _ = _svc([_var("v1", "suhu")])
    out = await svc.import_values(
        "n.csv", b"variable_code,period,value\nsuhu,2024-01-01,27\nsuhu,2024-02-01,-\nsuhu,2024-03-01,\n"
    )
    assert out["imported"] == 1
    assert out["skipped"] == {"suhu": 2}
    assert out["format"] == "long"


@pytest.mark.asyncio
async def test_import_format_lebar():
    """Tanpa kolom variable_code → format lebar: period [+ product_code] + satu kolom per kode."""
    svc, repo = _svc([_var("v1", "suhu"), _var("v2", "promo", "flag", "product")])
    body = (
        b"period,suhu,promo,kolom_aneh,product_code\n"
        b"2024-01-24,27.2,1,x,KBYPL 200\n"
        b"2024-02-24,-,0,y,KBYPL 200\n"
    )
    out = await svc.import_values("lebar.csv", body)

    assert out["format"] == "wide"
    assert out["imported"] == 3
    assert out["skipped"] == {"suhu": 1}
    assert out["warnings"] == ["Kolom tidak dikenal diabaikan: kolom_aneh."]
    suhu = [r for r in repo.values if r.variable_id == "v1"]
    assert [(r.period, float(r.value), r.product_id) for r in suhu] == [(date(2024, 1, 1), 27.2, None)]
    promo = sorted((r.period, float(r.value), r.product_id) for r in repo.values if r.variable_id == "v2")
    assert promo == [(date(2024, 1, 1), 1.0, "p1"), (date(2024, 2, 1), 0.0, "p1")]


@pytest.mark.asyncio
async def test_import_xlsx_lebar_sel_kotor_excel_thesis():
    """Sel teks seperti di sheet Pengumpulan Data: koma desimal + tab, `NA`, `-`."""
    svc, repo = _svc([_var("v1", "gt_yogurt"), _var("v2", "hari_promo")])
    content = _xlsx([
        {"period": date(2024, 4, 24), "gt_yogurt": "40,33\t", "hari_promo": 4},
        {"period": date(2024, 6, 24), "gt_yogurt": 38, "hari_promo": "NA"},
    ])
    out = await svc.import_values("pengumpulan.xlsx", content)

    assert out["imported"] == 3
    assert out["skipped"] == {"hari_promo": 1}
    gt = {r.period: float(r.value) for r in repo.values if r.variable_id == "v1"}
    assert gt == {date(2024, 4, 1): 40.33, date(2024, 6, 1): 38.0}


@pytest.mark.asyncio
async def test_import_format_lebar_tanpa_kolom_period():
    svc, _ = _svc([_var("v1", "suhu")])
    with pytest.raises(UploadInvalidFormatError, match="period"):
        await svc.import_values("x.csv", b"tanggal,suhu\n2024-01-01,27\n")


@pytest.mark.asyncio
async def test_import_dry_run_kumpulkan_semua_error():
    svc, repo = _svc([_var("v1", "suhu"), _var("v2", "promo", "flag")])
    body = (
        b"variable_code,period,value\n"
        b"suhu,2024-01-01,27\n"
        b"hujan,2024-01-01,1\n"
        b"suhu,bukan-tanggal,1\n"
        b"promo,2024-01-01,2\n"
    )
    out = await svc.import_values("n.csv", body, dry_run=True)

    assert out["dry_run"] is True and out["valid"] is False
    assert [e.split(":")[0] for e in out["errors"]] == ["Baris 3", "Baris 4", "Baris 5"]
    assert out["imported"] == 1  # yang AKAN diimpor bila error diperbaiki
    assert repo.values == []


@pytest.mark.asyncio
async def test_import_dry_run_valid_tidak_menulis():
    svc, repo = _svc([_var("v1", "suhu")])
    out = await svc.import_values("n.csv", b"variable_code,period,value\nsuhu,2024-01-24,27\n", dry_run=True)
    assert out["valid"] is True and out["errors"] == [] and out["imported"] == 1
    assert repo.values == []


@pytest.mark.asyncio
async def test_import_error_menyebut_jumlah_error_lain():
    svc, repo = _svc([_var("v1", "suhu")])
    body = b"variable_code,period,value\nhujan,2024-01-01,1\nsuhu,x,1\nsuhu,2024-01-01,abc\n"
    with pytest.raises(UploadInvalidFormatError, match=r"Baris 2: .*\(\+2 error lain"):
        await svc.import_values("n.csv", body)
    assert repo.values == []


@pytest.mark.asyncio
async def test_template_xlsx_header_saja_tanpa_baris_data():
    """21 Nov 2026 (keputusan user): template kosong — hanya header variabel AKTIF, tanpa baris
    periode dan tanpa nilai tersimpan (menggantikan template terisi CR v3.4 §4.3)."""
    svc, _ = _svc(
        [_var("v1", "suhu"), _var("v2", "promo", "flag", "product"), _var("v3", "tbi", active=False)],
        [_val("v1", date(2024, 1, 1), 27)],
        demand=FakeDemand(date(2024, 1, 1), date(2024, 2, 1)),
    )
    content, filename = await svc.template(horizon=1)
    df = pd.read_excel(io.BytesIO(content), sheet_name="nilai")

    assert filename.endswith(".xlsx")
    assert list(df.columns) == ["period", "product_code", "promo", "suhu"]
    assert df.empty


@pytest.mark.asyncio
async def test_template_tanpa_variabel_per_produk_tanpa_kolom_product_code():
    svc, _ = _svc([_var("v1", "suhu")], demand=FakeDemand(date(2024, 1, 1), date(2024, 1, 1)))
    content, _ = await svc.template(horizon=1)
    assert list(pd.read_excel(io.BytesIO(content), sheet_name="nilai").columns) == ["period", "suhu"]


@pytest.mark.asyncio
async def test_template_sheet_petunjuk_berisi_kode_dan_contoh_tanggal():
    svc, _ = _svc([_var("v1", "suhu")])
    content, _ = await svc.template(horizon=1)
    info = pd.read_excel(io.BytesIO(content), sheet_name="petunjuk", header=None).fillna("")
    text = " ".join(str(v) for v in info.values.ravel())
    assert "suhu" in text
    assert "2024-01-01" in text or "YYYY-MM-DD" in text


@pytest.mark.asyncio
async def test_template_diisi_lalu_diimport_ulang():
    """Round trip: template yang diisi planner bisa langsung diimport (format lebar)."""
    svc, _ = _svc([_var("v1", "suhu")], demand=FakeDemand(date(2024, 1, 1), date(2024, 1, 1)))
    content, _ = await svc.template(horizon=1)
    df = pd.read_excel(io.BytesIO(content), sheet_name="nilai")
    df = pd.DataFrame({"period": ["2024-01-01", "2024-02-01"], "suhu": [27.0, 28.0]})[list(df.columns)]
    buf = io.BytesIO()
    df.to_excel(buf, index=False, sheet_name="nilai")

    out = await svc.import_values("template.xlsx", buf.getvalue())
    assert out["imported"] == 2 and out["format"] == "wide"


# ── CR v3.4 §4.4 — peringatan kode kategori (non-blocking) ──


@pytest.mark.asyncio
async def test_import_peringatan_numeric_mirip_kode_kategori():
    svc, repo = _svc([_var("v1", "kode_musim"), _var("v2", "curah_hujan"), _var("v3", "hari_promo")])
    body = (
        b"period,kode_musim,curah_hujan,hari_promo\n"
        b"2024-01-01,1,2,0\n2024-02-01,2,2.5,4\n2024-03-01,3,3,1\n2024-04-01,1,1.5,2\n"
    )
    out = await svc.import_values("lebar.csv", body)

    assert out["imported"] == 12  # tetap diimport
    assert out["warnings"] == [
        "Variabel 'kode_musim' hanya berisi bilangan bulat 1–3: apakah ini kode kategori? "
        "Pertimbangkan satu variabel flag per kategori."
    ]


@pytest.mark.asyncio
async def test_import_flag_dan_dua_nilai_tidak_diperingatkan():
    svc, _ = _svc([_var("v1", "promo", "flag"), _var("v2", "shift")])
    body = b"period,promo,shift\n2024-01-01,1,1\n2024-02-01,0,2\n"
    out = await svc.import_values("lebar.csv", body)
    assert out["warnings"] == []


@pytest.mark.asyncio
async def test_import_lebar_tanggal_bentrok_satu_error_per_baris():
    """Format lebar: satu baris bertanggal salah → satu error, bukan satu per kolom variabel."""
    svc, _ = _svc([_var("v1", "suhu"), _var("v2", "inflasi"), _var("v3", "gt_yogurt")])
    body = b"period,suhu,inflasi,gt_yogurt\n2024-01-01,27,0.1,40\n2024-01-25,28,0.2,41\n"
    out = await svc.import_values("lebar.csv", body, dry_run=True)
    assert out["n_errors"] == 1
    assert out["errors"][0].startswith("Baris 3: periode 2024-01-25 jatuh di bulan yang sama dengan baris 2 (2024-01-01)")


@pytest.mark.asyncio
async def test_import_panjang_tanggal_bentrok_menyebut_variabel():
    svc, _ = _svc([_var("v1", "suhu")])
    body = b"variable_code,period,value\nsuhu,2024-01-01,27\nsuhu,2024-01-25,28\n"
    out = await svc.import_values("n.csv", body, dry_run=True)
    assert out["errors"][0].startswith("Baris 3: 'suhu' periode 2024-01-25 jatuh di bulan yang sama dengan baris 2")
