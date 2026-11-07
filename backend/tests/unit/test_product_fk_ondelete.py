"""
Hapus produk tidak boleh mentok di FK (regresi: DELETE /products/{id} → 500).

Kebijakan: konfigurasi turunan produk (BOM, warehouse_config) ikut terhapus; histori
(demand_history, forecast_results) dipertahankan dengan product_id di-NULL-kan —
demand_history tetap punya `product_code` sebagai jejak.
"""
import pytest

from app.models.bom import Bom
from app.models.demand_history import DemandHistory
from app.models.forecast_result import ForecastResult
from app.models.warehouse import WarehouseConfig


def _product_fk(model):
    (fk,) = [fk for fk in model.__table__.c.product_id.foreign_keys if fk.column.table.name == "products"]
    return fk


@pytest.mark.parametrize(
    ("model", "expected"),
    [
        (Bom, "CASCADE"),
        (WarehouseConfig, "CASCADE"),
        (DemandHistory, "SET NULL"),
        (ForecastResult, "SET NULL"),
    ],
)
def test_product_fk_ondelete(model, expected):
    assert _product_fk(model).ondelete == expected
