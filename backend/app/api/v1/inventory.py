"""
Stok ERP endpoints (Fase 11.5, 30 Oktober 2026) — REVISI_V2 §3.3/§5.1.

POST   /stock-snapshots/import          → upload stok ERP CSV/XLSX (admin/ppic)
GET    /stock-snapshots                 → daftar (?material_id=&date=)
GET    /stock-snapshots/latest          → stok terakhir per material (?as_of=)

Endpoint `/material-receipts*` (kedatangan manual) dihapus 20 Nov 2026 — kedatangan = pesanan
hasil ROP di proyeksi stok (`GET /forecast/runs/{id}/stock-projection`, kolom `order_qty`).
"""
from datetime import date

from fastapi import APIRouter, Depends, UploadFile

from app.api.deps import (
    get_current_user,
    get_stock_snapshot_service,
    require_role,
)
from app.services.inventory_data_service import StockSnapshotService

router = APIRouter(tags=["inventory"])
_WRITE = require_role("admin", "ppic")


def _snapshot(r) -> dict:
    return {
        "material_id": str(r.material_id),
        "snapshot_date": str(r.snapshot_date),
        "qty": float(r.qty),
        "uom": r.uom,
    }


@router.post("/stock-snapshots/import", dependencies=[Depends(_WRITE)])
async def import_stock_snapshots(file: UploadFile, service: StockSnapshotService = Depends(get_stock_snapshot_service)):
    result = await service.import_snapshots(file.filename or "", await file.read())
    return {"success": True, "data": result, "message": f"{result['imported']} stok material diimpor"}


@router.get("/stock-snapshots", dependencies=[Depends(get_current_user)])
async def list_stock_snapshots(
    material_id: str | None = None,
    date: date | None = None,
    service: StockSnapshotService = Depends(get_stock_snapshot_service),
):
    return {"success": True, "data": [_snapshot(r) for r in await service.list(material_id, date)]}


@router.get("/stock-snapshots/latest", dependencies=[Depends(get_current_user)])
async def latest_stock_snapshots(
    as_of: date | None = None, service: StockSnapshotService = Depends(get_stock_snapshot_service)
):
    latest = await service.latest_stock(as_of)
    data = [
        {"material_id": mid, "snapshot_date": str(d), "qty": qty} for mid, (d, qty) in sorted(latest.items())
    ]
    return {"success": True, "data": data}
