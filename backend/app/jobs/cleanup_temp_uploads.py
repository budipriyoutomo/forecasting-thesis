"""
Cron cleanup temp upload — docs/ARCHITECTURE.md §7 (jalankan tiap 30 menit).

Menghapus file temp di R2 untuk upload session yang masih `pending` dan sudah
lewat `expires_at`, lalu menandai statusnya `expired`. Sengaja TIDAK memakai
Celery/Redis (AGENTS.md §10 #11, MVP sync-first) — cukup dijadwalkan lewat cron
OS / scheduler platform (mis. Railway cron) memanggil:

    python -m app.jobs.cleanup_temp_uploads
"""
import asyncio

from app.repositories.upload_session_repository import (
    SqlConsumptionHistoryRepository,
    SqlUploadSessionRepository,
)
from app.repositories.material_repository import SqlMaterialRepository
from app.services.storage_service import StorageService, build_r2_client
from app.services.upload_service import UploadService
from app.db.session import get_sessionmaker


async def run() -> int:
    async with get_sessionmaker()() as session:
        service = UploadService(
            storage=StorageService(build_r2_client()),
            sessions=SqlUploadSessionRepository(session),
            consumptions=SqlConsumptionHistoryRepository(session),
            materials=SqlMaterialRepository(session),
        )
        count = await service.cleanup_expired()
        await session.commit()
        return count


def main() -> None:
    removed = asyncio.run(run())
    print(f"[cleanup_temp_uploads] {removed} temp upload session dibersihkan.")


if __name__ == "__main__":
    main()
