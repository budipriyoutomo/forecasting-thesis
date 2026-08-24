"""
Pydantic schemas untuk endpoint overrides — docs/ARCHITECTURE.md §4/§5.
"""
from typing import Literal

from pydantic import BaseModel


class OverrideCreateRequest(BaseModel):
    # target_type dibatasi Literal → nilai lain otomatis 422 (validasi Pydantic).
    target_type: Literal["forecast_result", "reorder_recommendation"]
    target_id: str
    new_value: dict
    reason: str = ""  # divalidasi di service: OVERRIDE_REASON_REQUIRED bila kosong


class OverrideOut(BaseModel):
    id: str
    target_type: str
    target_id: str
    user_id: str
    previous_value: dict | None
    new_value: dict
    reason: str
    created_at: str | None = None
