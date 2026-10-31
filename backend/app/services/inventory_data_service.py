"""
Stok ERP & estimasi kedatangan material (Fase 11.5, 30 Oktober 2026) — REVISI_V2 §3.3.

StockSnapshotService  : import snapshot (material_code, snapshot_date|date, qty [, uom]),
                        stok terakhir per material (opsional per tanggal acuan), dan rata-
                        rata nilai persediaan (Rp) untuk saran i (%) EOQ klasik (Keputusan #5).
MaterialReceiptService: CRUD kedatangan manual + import (material_code, expected_date, qty [, note]).
"""
from collections.abc import Callable
from datetime import date
from decimal import Decimal, InvalidOperation

import pandas as pd

from app.models.inventory import MaterialReceipt, StockSnapshot
from app.utils.exceptions import MaterialNotFoundError, MaterialReceiptNotFoundError, UploadInvalidFormatError
from app.utils.tabular import cell, read_table, require_columns


def _parse_date(raw, column: str, line: int) -> date:
    try:
        return pd.to_datetime(cell(raw)).date()
    except (ValueError, TypeError) as exc:
        raise UploadInvalidFormatError(f"Baris {line}: '{column}' bukan tanggal valid.") from exc


def _parse_qty(raw, line: int, positive: bool = False) -> Decimal:
    try:
        qty = Decimal(cell(raw))
    except InvalidOperation as exc:
        raise UploadInvalidFormatError(f"Baris {line}: 'qty' bukan angka valid.") from exc
    if positive and qty <= 0:
        raise UploadInvalidFormatError(f"Baris {line}: 'qty' harus lebih dari 0.")
    if qty < 0:
        raise UploadInvalidFormatError(f"Baris {line}: 'qty' tidak boleh negatif.")
    return qty


async def _material_by_code(materials, cache: dict, code: str, line: int):
    if code not in cache:
        cache[code] = await materials.get_by_code(code)
    if cache[code] is None:
        raise UploadInvalidFormatError(f"Baris {line}: Material '{code}' tidak ditemukan.")
    return cache[code]


def _rows(filename: str, content: bytes, required: set[str], aliases: dict[str, str]):
    df = read_table(filename, content).rename(columns=aliases)
    require_columns(df, required)
    if df.empty:
        raise UploadInvalidFormatError("File tidak berisi baris data.")
    return list(enumerate(df.to_dict("records"), start=2))


class StockSnapshotService:
    def __init__(self, repo, materials, factory: Callable[..., object] = StockSnapshot):
        self._repo = repo
        self._materials = materials
        self._factory = factory

    async def list(self, material_id: str | None = None, snapshot_date: date | None = None):
        return await self._repo.list(material_id, snapshot_date)

    async def import_snapshots(self, filename: str, content: bytes) -> dict:
        records = _rows(filename, content, {"material_code", "snapshot_date", "qty"}, {"date": "snapshot_date"})
        cache: dict = {}
        rows, seen = [], set()
        for line, raw in records:
            material = await _material_by_code(self._materials, cache, cell(raw.get("material_code")), line)
            snapshot_date = _parse_date(raw.get("snapshot_date"), "snapshot_date", line)
            key = (str(material.id), snapshot_date)
            if key in seen:
                raise UploadInvalidFormatError(f"Baris {line}: material & tanggal duplikat di file.")
            seen.add(key)
            rows.append(
                self._factory(
                    material_id=material.id,
                    snapshot_date=snapshot_date,
                    qty=_parse_qty(raw.get("qty"), line),
                    uom=cell(raw.get("uom")) or None,
                )
            )
        return {"imported": await self._repo.upsert(rows)}

    async def latest_stock(self, as_of: date | None = None) -> dict[str, tuple[date, float]]:
        """{material_id: (tanggal snapshot, qty)} — snapshot terakhir ≤ `as_of` (None = terbaru)."""
        latest: dict[str, tuple[date, float]] = {}
        for r in await self._repo.list():
            if as_of is not None and r.snapshot_date > as_of:
                continue
            mid = str(r.material_id)
            if mid not in latest or r.snapshot_date > latest[mid][0]:
                latest[mid] = (r.snapshot_date, float(r.qty))
        return latest

    async def average_inventory_value(self) -> float | None:
        """Rata-rata Σ(qty × harga) per tanggal snapshot. Material tanpa harga dilewati."""
        prices = {str(m.id): getattr(m, "unit_price", None) for m in await self._materials.list()}
        by_date: dict[date, float] = {}
        for r in await self._repo.list():
            price = prices.get(str(r.material_id))
            if price is None:
                continue
            by_date[r.snapshot_date] = by_date.get(r.snapshot_date, 0.0) + float(r.qty) * float(price)
        if not by_date:
            return None
        return sum(by_date.values()) / len(by_date)


class MaterialReceiptService:
    def __init__(self, repo, materials, factory: Callable[..., object] = MaterialReceipt):
        self._repo = repo
        self._materials = materials
        self._factory = factory

    async def list(self, material_id: str | None = None, date_from: date | None = None, date_to: date | None = None):
        return await self._repo.list(material_id, date_from, date_to)

    async def get(self, receipt_id: str):
        row = await self._repo.get_by_id(receipt_id)
        if row is None:
            raise MaterialReceiptNotFoundError("Rencana kedatangan material tidak ditemukan.")
        return row

    async def create(self, payload, user_id: str):
        if await self._materials.get_by_id(payload.material_id) is None:
            raise MaterialNotFoundError(f"Material '{payload.material_id}' tidak ditemukan.")
        row = self._factory(
            material_id=payload.material_id,
            expected_date=payload.expected_date,
            qty=Decimal(str(payload.qty)),
            note=payload.note,
            source="manual",
            created_by=user_id,
        )
        return await self._repo.add(row)

    async def update(self, receipt_id: str, payload):
        row = await self.get(receipt_id)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(row, field, Decimal(str(value)) if field == "qty" else value)
        return await self._repo.save(row)

    async def delete(self, receipt_id: str) -> None:
        await self._repo.delete(await self.get(receipt_id))

    async def import_receipts(self, filename: str, content: bytes, user_id: str) -> dict:
        records = _rows(filename, content, {"material_code", "expected_date", "qty"}, {"date": "expected_date"})
        cache: dict = {}
        rows = []
        for line, raw in records:
            material = await _material_by_code(self._materials, cache, cell(raw.get("material_code")), line)
            rows.append(
                self._factory(
                    material_id=material.id,
                    expected_date=_parse_date(raw.get("expected_date"), "expected_date", line),
                    qty=_parse_qty(raw.get("qty"), line, positive=True),
                    note=cell(raw.get("note")) or None,
                    source="upload",
                    created_by=user_id,
                )
            )
        return {"imported": await self._repo.add_all(rows)}
