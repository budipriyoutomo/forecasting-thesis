"""
Fase 3 — UploadService: persist upload + consumption, move ke permanent,
riwayat, guard SESSION_EXPIRED, cleanup. Semua dependency di-mock (tanpa DB/R2).
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from app.services.upload_service import UploadService
from app.utils.exceptions import (
    ForbiddenRoleError,
    InsufficientDataError,
    SessionExpiredError,
    SessionNotFoundError,
    UploadFileTooLargeError,
    UploadInvalidFormatError,
)

USER = "00000000-0000-0000-0000-000000000001"
OTHER = "00000000-0000-0000-0000-000000000002"


def _csv(n=12, materials=3) -> bytes:
    rows = ["material_code,date,quantity"]
    for i in range(n):
        rows.append(f"MAT-{i % materials:03d},2026-0{(i % 6) + 1}-01,{10 + i}")
    return "\n".join(rows).encode("utf-8")


class FakeSessionRepo:
    def __init__(self):
        self.items = {}

    async def add(self, upload):
        self.items[str(upload.id)] = upload
        return upload

    async def get_by_id(self, sid):
        return self.items.get(str(sid))

    async def list_by_user(self, user_id):
        return [s for s in self.items.values() if str(s.user_id) == str(user_id)]

    async def list_expired_pending(self, now):
        return [
            s for s in self.items.values() if s.status == "pending" and s.expires_at < now
        ]

    async def save(self, upload):
        return upload


class FakeConsumptionRepo:
    def __init__(self):
        self.rows = []

    async def bulk_add(self, rows):
        self.rows.extend(rows)
        return len(rows)


class FakeMaterialRepo:
    def __init__(self, mapping=None):
        self._map = mapping or {}

    async def map_codes_to_ids(self, codes):
        return {c: self._map[c] for c in codes if c in self._map}


def _service(storage=None, materials_map=None):
    storage = storage or MagicMock()
    storage.upload_temp.return_value = "temp/uploads/x/data.csv"
    storage.move_to_permanent.return_value = "permanent/datasets/u/x/raw.csv"
    return UploadService(
        storage=storage,
        sessions=FakeSessionRepo(),
        consumptions=FakeConsumptionRepo(),
        materials=FakeMaterialRepo(materials_map),
    )


@pytest.mark.asyncio
async def test_create_happy_path_persist_dan_move_ke_permanent():
    svc = _service()

    session = await svc.create_from_upload(USER, "data.csv", _csv())

    assert session.status == "validated"
    assert session.n_rows == 12
    assert session.n_materials_detected == 3
    assert session.file_url.startswith("permanent/")
    svc._storage.upload_temp.assert_called_once()
    svc._storage.move_to_permanent.assert_called_once()
    # consumption_history ikut tersimpan
    assert len(svc._consumptions.rows) == 12


@pytest.mark.asyncio
async def test_create_resolve_material_id_bila_kode_terdaftar():
    svc = _service(materials_map={"MAT-000": "id-000"})

    await svc.create_from_upload(USER, "data.csv", _csv(n=12, materials=3))

    resolved = [r for r in svc._consumptions.rows if r.material_code == "MAT-000"]
    assert resolved and all(r.material_id == "id-000" for r in resolved)
    # kode yang tak terdaftar → material_id None
    unresolved = [r for r in svc._consumptions.rows if r.material_code == "MAT-001"]
    assert unresolved and all(r.material_id is None for r in unresolved)


@pytest.mark.asyncio
async def test_create_file_terlalu_besar():
    svc = _service()
    big = b"x" * (11 * 1024 * 1024)  # > 10 MB default

    with pytest.raises(UploadFileTooLargeError):
        await svc.create_from_upload(USER, "data.csv", big)


@pytest.mark.asyncio
async def test_create_format_invalid_diteruskan():
    svc = _service()
    with pytest.raises(UploadInvalidFormatError):
        await svc.create_from_upload(USER, "data.txt", _csv())


@pytest.mark.asyncio
async def test_create_insufficient_data_diteruskan():
    svc = _service()
    with pytest.raises(InsufficientDataError):
        await svc.create_from_upload(USER, "data.csv", b"material_code,date,quantity\nMAT-1,2026-01-01,5\n")


@pytest.mark.asyncio
async def test_list_sessions_milik_user():
    svc = _service()
    await svc.create_from_upload(USER, "a.csv", _csv())
    await svc.create_from_upload(OTHER, "b.csv", _csv())

    mine = await svc.list_sessions(USER)

    assert len(mine) == 1


@pytest.mark.asyncio
async def test_get_session_tidak_ada_404():
    svc = _service()
    with pytest.raises(SessionNotFoundError):
        await svc.get_session(USER, "tidak-ada")


@pytest.mark.asyncio
async def test_get_session_milik_user_lain_403():
    svc = _service()
    session = await svc.create_from_upload(OTHER, "b.csv", _csv())

    with pytest.raises(ForbiddenRoleError):
        await svc.get_session(USER, str(session.id))


@pytest.mark.asyncio
async def test_get_session_pending_kedaluwarsa_session_expired():
    svc = _service()
    # buat session pending yang sudah lewat expires_at
    from app.models.upload_session import UploadSession

    past = datetime.now(timezone.utc) - timedelta(hours=2)
    s = UploadSession(
        id="expired-1", user_id=USER, file_name="x.csv", file_url="temp/...",
        file_size_kb=1, n_rows=0, n_materials_detected=0, status="pending", expires_at=past,
    )
    await svc._sessions.add(s)

    with pytest.raises(SessionExpiredError):
        await svc.get_session(USER, "expired-1")


@pytest.mark.asyncio
async def test_cleanup_expired_hapus_temp_dan_tandai_expired():
    svc = _service()
    from app.models.upload_session import UploadSession

    past = datetime.now(timezone.utc) - timedelta(hours=2)
    s = UploadSession(
        id="expired-1", user_id=USER, file_name="x.csv", file_url="temp/uploads/expired-1/x.csv",
        file_size_kb=1, n_rows=0, n_materials_detected=0, status="pending", expires_at=past,
    )
    await svc._sessions.add(s)

    count = await svc.cleanup_expired(now=datetime.now(timezone.utc))

    assert count == 1
    assert s.status == "expired"
    svc._storage.delete_temp.assert_called_once()
