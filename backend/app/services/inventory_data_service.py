"""
Stok ERP (Fase 11.5, 30 Oktober 2026) — REVISI_V2 §3.3.

StockSnapshotService  : import snapshot (material_code, snapshot_date|date, qty [, uom]),
                        stok terakhir per material (opsional per tanggal acuan), dan rata-
                        rata nilai persediaan (Rp) untuk saran i (%) EOQ klasik (Keputusan #5).
Input kedatangan manual (`MaterialReceiptService`) dihapus 20 Nov 2026: kedatangan = pesanan hasil
ROP di proyeksi stok (RECONCILIATION §"Kedatangan Material = Hasil Hitungan ROP").
"""
from collections.abc import Callable
from datetime import date
from decimal import Decimal

from app.models.inventory import StockSnapshot
from app.utils.exceptions import UploadInvalidFormatError
from app.utils.tabular import cell, is_blank_row, parse_decimal_id, parse_iso_date, read_table, require_columns

# Batas kolom DB — di luar ini INSERT gagal dan dulu muncul sebagai 500 INTERNAL_ERROR.
_MAX_QTY = Decimal(10) ** 14  # Numeric(18, 4)
_MAX_UOM = 20  # String(20)


def _parse_date(raw, column: str, line: int) -> date:
    try:
        value = parse_iso_date(raw)
    except ValueError as exc:
        raise UploadInvalidFormatError(
            f"Baris {line}: '{column}' bukan tanggal valid (format YYYY-MM-DD)."
        ) from exc
    if value is None:
        raise UploadInvalidFormatError(f"Baris {line}: '{column}' wajib diisi (format YYYY-MM-DD).")
    return value


def _parse_qty(raw, line: int) -> Decimal:
    try:
        qty = parse_decimal_id(raw)  # desimal titik atau koma (CSV Excel Indonesia)
    except ValueError as exc:
        raise UploadInvalidFormatError(f"Baris {line}: 'qty' bukan angka valid.") from exc
    if qty is None:
        raise UploadInvalidFormatError(f"Baris {line}: 'qty' wajib diisi.")
    if qty < 0:
        raise UploadInvalidFormatError(f"Baris {line}: 'qty' tidak boleh negatif.")
    if qty >= _MAX_QTY:
        raise UploadInvalidFormatError(f"Baris {line}: 'qty' terlalu besar.")
    return qty


def _parse_uom(raw, line: int) -> str | None:
    uom = cell(raw) or None
    if uom is not None and len(uom) > _MAX_UOM:
        raise UploadInvalidFormatError(f"Baris {line}: 'uom' maksimal {_MAX_UOM} karakter.")
    return uom


async def _material_by_code(materials, cache: dict, code: str, line: int):
    if code == "":
        raise UploadInvalidFormatError(f"Baris {line}: 'material_code' wajib diisi.")
    if code not in cache:
        cache[code] = await materials.get_by_code(code)
    if cache[code] is None:
        raise UploadInvalidFormatError(f"Baris {line}: Material '{code}' tidak ditemukan.")
    return cache[code]


def _rows(filename: str, content: bytes, required: set[str], aliases: dict[str, str]):
    df = read_table(filename, content).rename(columns=aliases)
    require_columns(df, required)
    # Nomor baris file (header = 1) dihitung sebelum baris kosong di tengah dilewati.
    records = [(line, r) for line, r in enumerate(df.to_dict("records"), start=2) if not is_blank_row(r)]
    if not records:
        raise UploadInvalidFormatError("File tidak berisi baris data.")
    return records


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
                    uom=_parse_uom(raw.get("uom"), line),
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
