"""
Fase 11.1 — import pemakaian aktual material + faktor waste per material (buffer stock).

Import (CSV/XLSX): material_code, period, actual_usage, dan salah satu:
  - standard_usage, atau
  - product_code + production_output → standar = output × qty BOM (produk, material)
Faktor waste material = Σ aktual ÷ Σ standar (agregat seluruh periode tersimpan).
"""
from datetime import date
from types import SimpleNamespace

import pytest

from app.services.material_usage_service import MaterialUsageService
from app.utils.exceptions import UploadInvalidFormatError


class FakeUsageRepo:
    def __init__(self, rows=None):
        self.rows = list(rows or [])

    async def upsert(self, rows):
        keys = {(str(r.material_id), str(r.product_id), r.period) for r in rows}
        self.rows = [r for r in self.rows if (str(r.material_id), str(r.product_id), r.period) not in keys]
        self.rows.extend(rows)
        return len(rows)

    async def list(self, material_id=None):
        return [r for r in self.rows if material_id is None or str(r.material_id) == str(material_id)]

    async def totals_by_material(self, material_ids=None):
        out = {}
        for r in self.rows:
            if material_ids is not None and str(r.material_id) not in {str(m) for m in material_ids}:
                continue
            a, s = out.get(str(r.material_id), (0.0, 0.0))
            out[str(r.material_id)] = (a + float(r.actual_usage), s + float(r.standard_usage))
        return out


class ByCode:
    def __init__(self, items):
        self._by = {i.code: i for i in items}

    async def get_by_code(self, code):
        return self._by.get(code)


class FakeBoms:
    def __init__(self, lines):
        self._lines = lines

    async def list(self, product_id=None):
        return [b for b in self._lines if product_id is None or str(b.product_id) == str(product_id)]


M1 = SimpleNamespace(id="m1", code="CAP-WHITE")
M2 = SimpleNamespace(id="m2", code="BTL-WHITE")
P1 = SimpleNamespace(id="p1", code="KBYPL 200")


def _svc(rows=None, boms=None):
    repo = FakeUsageRepo(rows)
    svc = MaterialUsageService(
        repo,
        materials=ByCode([M1, M2]),
        products=ByCode([P1]),
        boms=FakeBoms(boms or [SimpleNamespace(product_id="p1", material_id="m1", qty_per_unit=2)]),
        factory=lambda **kw: SimpleNamespace(**kw),
    )
    return svc, repo


@pytest.mark.asyncio
async def test_import_standar_langsung_dan_dari_output_x_bom():
    svc, repo = _svc()
    body = (
        "material_code,period,actual_usage,standard_usage,product_code,production_output\n"
        "BTL-WHITE,2026-01-01,1030,1000,,\n"
        "CAP-WHITE,2026-01-01,2100,,KBYPL 200,1000\n"
    )
    assert await svc.import_usage("u.csv", body.encode()) == {"imported": 2}

    cap = next(r for r in repo.rows if r.material_id == "m1")
    assert float(cap.standard_usage) == 2000  # 1000 × BOM 2
    assert float(cap.production_output) == 1000 and cap.product_id == "p1"


@pytest.mark.parametrize(
    "body,match",
    [
        ("material_code,period,actual_usage\nBTL-WHITE,2026-01-01,10\n", "standard_usage"),
        ("material_code,period,actual_usage,standard_usage\nXX,2026-01-01,10,10\n", "Material"),
        ("material_code,period,actual_usage,product_code,production_output\nBTL-WHITE,2026-01-01,10,KBYPL 200,5\n", "BOM"),
        ("material_code,period,actual_usage,product_code,production_output\nCAP-WHITE,2026-01-01,10,ZZ,5\n", "Produk"),
        ("material_code,period,actual_usage,standard_usage\nBTL-WHITE,2026-01-01,-1,10\n", "negatif"),
        ("material_code,period,actual_usage,standard_usage\nBTL-WHITE,xx,1,10\n", "period"),
        ("material_code,period,standard_usage\nBTL-WHITE,2026-01-01,10\n", "actual_usage"),
    ],
)
@pytest.mark.asyncio
async def test_import_tidak_valid(body, match):
    svc, repo = _svc()
    with pytest.raises(UploadInvalidFormatError, match=match):
        await svc.import_usage("u.csv", body.encode())
    assert repo.rows == []


@pytest.mark.asyncio
async def test_waste_factor_agregat_per_material():
    rows = [
        SimpleNamespace(material_id="m2", product_id=None, period=date(2026, 1, 1), actual_usage=1030, standard_usage=1000),
        SimpleNamespace(material_id="m2", product_id=None, period=date(2026, 2, 1), actual_usage=1010, standard_usage=1000),
        SimpleNamespace(material_id="m1", product_id=None, period=date(2026, 1, 1), actual_usage=5, standard_usage=0),
    ]
    svc, _ = _svc(rows)
    factors = await svc.waste_factors()

    assert factors["m2"] == pytest.approx(2040 / 2000)  # Σ aktual ÷ Σ standar, bukan rata-rata rasio
    assert factors["m1"] is None  # standar 0 → tak terdefinisi
