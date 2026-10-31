"""
Fase 11.2b — master data variabel eksternal (Keputusan #7, docs/REVISI_V2.md §6.1).

Variabel dinamis (kode, nama, tipe numeric/flag, scope global/product) dengan toggle
aktif/nonaktif; nilai per periode di-upload. Hanya variabel AKTIF yang dipakai engine ML.
"""
from datetime import date
from types import SimpleNamespace

import pandas as pd
import pytest

from app.schemas.external_variable import ExternalVariableCreate, ExternalVariableUpdate
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

    async def count_values(self):
        out = {}
        for r in self.values:
            out[str(r.variable_id)] = out.get(str(r.variable_id), 0) + 1
        return out


class FakeProducts:
    def __init__(self, products):
        self._by_code = {p.code: p for p in products}

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


def _svc(variables=None, values=None):
    repo = FakeVarRepo(variables, values)
    return ExternalVariableService(
        repo, FakeProducts([P1]), var_factory=_var_factory, value_factory=_val_factory
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

    assert out == {"imported": 3}
    promo = [r for r in repo.values if r.variable_id == "v2"][0]
    assert promo.product_id == "p1" and float(promo.value) == 1
    assert all(r.product_id is None for r in repo.values if r.variable_id == "v1")


@pytest.mark.asyncio
async def test_import_menimpa_nilai_periode_sama():
    svc, repo = _svc([_var("v1", "suhu")], [_val("v1", date(2026, 1, 1), 99)])
    await svc.import_values("n.csv", b"variable_code,period,value\nsuhu,2026-01-01,30\n")
    assert [float(r.value) for r in repo.values] == [30]


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
