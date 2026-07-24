"""
MaterialService — CRUD master data material + import CSV (Fase 2).

Repository injectable (mudah dites tanpa DB). `model_factory` memisahkan
pembuatan instance ORM dari logika bisnis supaya test bisa memakai objek palsu.
"""
import csv as csv_module
import io
from decimal import Decimal, InvalidOperation
from typing import Callable, Protocol

from app.models.material import Material
from app.schemas.material import MaterialCreate, MaterialUpdate
from app.utils.exceptions import (
    MaterialCodeExistsError,
    MaterialNotFoundError,
    UploadInvalidFormatError,
)

REQUIRED_IMPORT_COLUMNS = {"code", "name", "unit"}
OPTIONAL_IMPORT_COLUMNS = {"category", "lead_time_days", "moq", "manual_safety_stock"}


class _MaterialRepository(Protocol):
    async def list(self): ...
    async def get_by_id(self, material_id: str): ...
    async def get_by_code(self, code: str): ...
    async def add(self, material): ...
    async def save(self, material): ...
    async def delete(self, material): ...


class MaterialService:
    def __init__(self, repo: _MaterialRepository, model_factory: Callable[..., object] = Material):
        self._repo = repo
        self._model = model_factory

    async def list(self):
        return await self._repo.list()

    async def get(self, material_id: str):
        material = await self._repo.get_by_id(material_id)
        if material is None:
            raise MaterialNotFoundError("Material tidak ditemukan.")
        return material

    async def create(self, payload: MaterialCreate):
        if await self._repo.get_by_code(payload.code) is not None:
            raise MaterialCodeExistsError(f"Kode material '{payload.code}' sudah dipakai.")
        material = self._model(**payload.model_dump())
        return await self._repo.add(material)

    async def update(self, material_id: str, payload: MaterialUpdate):
        material = await self.get(material_id)
        changes = payload.model_dump(exclude_unset=True)

        new_code = changes.get("code")
        if new_code and new_code != material.code:
            existing = await self._repo.get_by_code(new_code)
            if existing is not None and getattr(existing, "id", None) != material.id:
                raise MaterialCodeExistsError(f"Kode material '{new_code}' sudah dipakai.")

        for field, value in changes.items():
            setattr(material, field, value)
        return await self._repo.save(material)

    async def delete(self, material_id: str) -> None:
        material = await self.get(material_id)
        await self._repo.delete(material)

    async def import_csv(self, content: bytes) -> dict:
        try:
            text = content.decode("utf-8-sig")
        except UnicodeDecodeError as exc:
            raise UploadInvalidFormatError("File bukan CSV UTF-8 yang valid.") from exc

        reader = csv_module.DictReader(io.StringIO(text))
        headers = {h.strip() for h in (reader.fieldnames or [])}
        missing = REQUIRED_IMPORT_COLUMNS - headers
        if missing:
            raise UploadInvalidFormatError(f"Kolom wajib hilang: {', '.join(sorted(missing))}.")

        rows = [self._parse_row(row, i) for i, row in enumerate(reader, start=2)]
        if not rows:
            raise UploadInvalidFormatError("File tidak berisi baris data.")

        # Duplikat di dalam file → tolak sebelum menyentuh DB.
        seen: set[str] = set()
        for payload in rows:
            if payload.code in seen:
                raise MaterialCodeExistsError(f"Kode '{payload.code}' muncul lebih dari sekali di file.")
            seen.add(payload.code)

        for payload in rows:
            await self.create(payload)
        return {"imported": len(rows)}

    def _parse_row(self, row: dict, line: int) -> MaterialCreate:
        def num(key: str) -> Decimal | None:
            raw = (row.get(key) or "").strip()
            if raw == "":
                return None
            try:
                return Decimal(raw)
            except InvalidOperation as exc:
                raise UploadInvalidFormatError(f"Baris {line}: '{key}' bukan angka valid.") from exc

        lead = (row.get("lead_time_days") or "").strip()
        try:
            lead_days = int(lead) if lead else 0
        except ValueError as exc:
            raise UploadInvalidFormatError(f"Baris {line}: 'lead_time_days' bukan bilangan bulat.") from exc

        code = (row.get("code") or "").strip()
        name = (row.get("name") or "").strip()
        unit = (row.get("unit") or "").strip()
        if not code or not name or not unit:
            raise UploadInvalidFormatError(f"Baris {line}: code/name/unit tidak boleh kosong.")

        return MaterialCreate(
            code=code,
            name=name,
            category=(row.get("category") or "").strip() or None,
            unit=unit,
            lead_time_days=lead_days,
            moq=num("moq") or Decimal(0),
            manual_safety_stock=num("manual_safety_stock"),
        )
