"""
UploadService — orkestrasi ingestion (Fase 3), docs/ARCHITECTURE.md §3/§7.

Alur POST upload (single-step, langsung divalidasi):
  1. Cek ukuran file (UPLOAD_FILE_TOO_LARGE).
  2. Parse + validasi CSV (UPLOAD_INVALID_FORMAT / INSUFFICIENT_DATA).
  3. Simpan file ke R2 temp, lalu move ke permanent (STORAGE_UPLOAD_FAILED).
  4. Persist upload_session (status=validated) + consumption_history.
     material_id di-resolve dari master data; kode yang belum terdaftar diberi
     warning tanpa auto-create material (AGENTS.md §6, lihat RECONCILIATION #14).

Semua dependency injectable → mudah dites tanpa DB/R2 nyata.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Protocol

from app.config import get_settings
from app.models.consumption_history import ConsumptionHistory
from app.models.upload_session import UploadSession
from app.services import data_ingestion_service
from app.utils.exceptions import (
    ForbiddenRoleError,
    SessionExpiredError,
    SessionNotFoundError,
    UploadFileTooLargeError,
)

TEMP_TTL = timedelta(hours=1)


class _Storage(Protocol):
    def upload_temp(self, session_id: str, filename: str, content: bytes) -> str: ...
    def move_to_permanent(self, user_id: str, session_id: str, filename: str) -> str: ...
    def delete_temp(self, session_id: str, filename: str) -> None: ...


class UploadService:
    def __init__(self, storage: _Storage, sessions, consumptions, materials):
        self._storage = storage
        self._sessions = sessions
        self._consumptions = consumptions
        self._materials = materials

    async def create_from_upload(
        self, user_id: str, filename: str, content: bytes, now: datetime | None = None
    ) -> UploadSession:
        now = now or datetime.now(timezone.utc)
        settings = get_settings()

        max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
        if len(content) > max_bytes:
            raise UploadFileTooLargeError(
                f"Ukuran file melebihi batas {settings.MAX_UPLOAD_SIZE_MB} MB."
            )

        # Validasi dulu sebelum menyentuh storage — gagal cepat, tidak menaruh sampah di R2.
        summary = data_ingestion_service.parse_and_validate_csv(filename, content)

        session_id = str(uuid.uuid4())
        self._storage.upload_temp(session_id, filename, content)
        permanent_url = self._storage.move_to_permanent(user_id, session_id, filename)

        rows = data_ingestion_service.extract_consumption_rows(content)
        codes = {r["material_code"] for r in rows}
        code_to_id = await self._materials.map_codes_to_ids(codes)

        warnings = list(summary.get("warnings") or [])
        unknown = sorted(codes - code_to_id.keys())
        if unknown:
            warnings.append(
                f"{len(unknown)} kode material belum terdaftar di master data: "
                f"{', '.join(unknown[:5])}{'…' if len(unknown) > 5 else ''}"
            )

        session = UploadSession(
            id=session_id,
            user_id=user_id,
            file_name=filename,
            file_url=permanent_url,
            file_size_kb=max(1, len(content) // 1024),
            n_rows=summary["n_rows"],
            n_materials_detected=summary["n_materials_detected"],
            preview_data=summary["preview"],
            warnings=warnings,
            status="validated",
            expires_at=now + TEMP_TTL,
        )
        await self._sessions.add(session)

        history = [
            ConsumptionHistory(
                material_code=r["material_code"],
                material_id=code_to_id.get(r["material_code"]),
                date=r["date"],
                quantity=r["quantity"],
                upload_session_id=session_id,
            )
            for r in rows
        ]
        if history:
            await self._consumptions.bulk_add(history)

        return session

    async def list_sessions(self, user_id: str) -> list[UploadSession]:
        return await self._sessions.list_by_user(user_id)

    async def get_session(
        self, user_id: str, session_id: str, now: datetime | None = None
    ) -> UploadSession:
        now = now or datetime.now(timezone.utc)
        session = await self._sessions.get_by_id(session_id)
        if session is None:
            raise SessionNotFoundError("Upload session tidak ditemukan.")
        if str(session.user_id) != str(user_id):
            raise ForbiddenRoleError("Anda tidak berhak mengakses upload ini.")
        if session.status == "pending" and session.expires_at < now:
            raise SessionExpiredError("Upload session sudah kedaluwarsa.")
        return session

    async def cleanup_expired(self, now: datetime | None = None) -> int:
        """Dipakai cron cleanup (docs/ARCHITECTURE.md §7): hapus temp yang expired."""
        now = now or datetime.now(timezone.utc)
        expired = await self._sessions.list_expired_pending(now)
        for session in expired:
            try:
                self._storage.delete_temp(str(session.id), session.file_name)
            except Exception:
                # Kegagalan hapus 1 file tidak boleh menggagalkan cleanup lainnya.
                pass
            session.status = "expired"
            await self._sessions.save(session)
        return len(expired)
