"""
Schemas variabel eksternal (Fase 11.2b) — docs/ARCHITECTURE.md §5.

`code` dipakai langsung sebagai nama fitur ML → snake_case, tidak boleh bentrok dengan
fitur bawaan (`month`, `lag_<n>`).
"""
import re
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

_CODE = re.compile(r"^[a-z][a-z0-9_]{0,49}$")
_RESERVED = re.compile(r"^(month|lag_\d+)$")

ValueType = Literal["numeric", "flag"]
Scope = Literal["global", "product"]


def _check_code(code: str) -> str:
    if not _CODE.match(code):
        raise ValueError("Kode harus snake_case huruf kecil (a–z, 0–9, _) dan diawali huruf.")
    if _RESERVED.match(code):
        raise ValueError(f"Kode '{code}' bentrok dengan fitur bawaan model.")
    return code


class ExternalVariableCreate(BaseModel):
    code: str
    name: str = Field(min_length=1, max_length=100)
    value_type: ValueType = "numeric"
    scope: Scope = "global"
    unit: str | None = Field(default=None, max_length=20)
    description: str | None = None
    is_active: bool = True

    _code = field_validator("code")(classmethod(lambda cls, v: _check_code(v)))


class ExternalVariableUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    value_type: ValueType | None = None
    scope: Scope | None = None
    unit: str | None = Field(default=None, max_length=20)
    description: str | None = None
    is_active: bool | None = None


class ExternalVariableOut(BaseModel):
    id: str
    code: str
    name: str
    value_type: ValueType
    scope: Scope
    unit: str | None = None
    description: str | None = None
    is_active: bool
    n_values: int = 0
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ExternalVariableValueOut(BaseModel):
    product_id: str | None = None
    period: date
    value: float
