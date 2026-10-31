"""
Stok ERP & kedatangan material endpoints (Fase 11.5, 30 Oktober 2026) — REVISI_V2 §3.3/§5.1.

POST   /stock-snapshots/import          → upload stok ERP CSV/XLSX (admin/ppic)
GET    /stock-snapshots                 → daftar (?material_id=&date=)
GET    /stock-snapshots/latest          → stok terakhir per material (?as_of=)
GET    /material-receipts               → daftar (?material_id=&date_from=&date_to=)
POST   /material-receipts               → input manual (admin/ppic)
POST   /material-receipts/import        → upload CSV/XLSX (admin/ppic)
PUT    /material-receipts/{id}          → ubah (admin/ppic)
DELETE /material-receipts/{id}          → hapus (admin/ppic)
"""
from datetime import date

from fastapi import APIRouter, Depends, UploadFile
from fastapi.responses import JSONResponse

from app.api.deps import (
    CurrentUser,
    get_current_user,
    get_material_receipt_service,
    get_stock_snapshot_service,
    require_role,
)
from app.schemas.inventory import MaterialReceiptCreate, MaterialReceiptUpdate
from app.services.inventory_data_service import MaterialReceiptService, StockSnapshotService

router = APIRouter(tags=["inventory"])
_WRITE = require_role("admin", "ppic")


def _snapshot(r) -> dict:
    return {
        "material_id": str(r.material_id),
        "snapshot_date": str(r.snapshot_date),
        "qty": float(r.qty),
        "uom": r.uom,
    }


def _receipt(r) -> dict:
    return {
        "id": str(r.id),
        "material_id": str(r.material_id),
        "expected_date": str(r.expected_date),
        "qty": float(r.qty),
        "source": r.source,
        "note": r.note,
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


@router.get("/material-receipts", dependencies=[Depends(get_current_user)])
async def list_material_receipts(
    material_id: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    service: MaterialReceiptService = Depends(get_material_receipt_service),
):
    return {"success": True, "data": [_receipt(r) for r in await service.list(material_id, date_from, date_to)]}


@router.post("/material-receipts")
async def create_material_receipt(
    payload: MaterialReceiptCreate,
    current_user: CurrentUser = Depends(_WRITE),
    service: MaterialReceiptService = Depends(get_material_receipt_service),
):
    row = await service.create(payload, current_user.user_id)
    return JSONResponse(status_code=201, content={"success": True, "data": _receipt(row)})


@router.post("/material-receipts/import")
async def import_material_receipts(
    file: UploadFile,
    current_user: CurrentUser = Depends(_WRITE),
    service: MaterialReceiptService = Depends(get_material_receipt_service),
):
    result = await service.import_receipts(file.filename or "", await file.read(), current_user.user_id)
    return {"success": True, "data": result, "message": f"{result['imported']} kedatangan diimpor"}


@router.put("/material-receipts/{receipt_id}", dependencies=[Depends(_WRITE)])
async def update_material_receipt(
    receipt_id: str,
    payload: MaterialReceiptUpdate,
    service: MaterialReceiptService = Depends(get_material_receipt_service),
):
    return {"success": True, "data": _receipt(await service.update(receipt_id, payload))}


@router.delete("/material-receipts/{receipt_id}", dependencies=[Depends(_WRITE)])
async def delete_material_receipt(
    receipt_id: str, service: MaterialReceiptService = Depends(get_material_receipt_service)
):
    await service.delete(receipt_id)
    return {"success": True, "data": {"id": receipt_id, "deleted": True}}
