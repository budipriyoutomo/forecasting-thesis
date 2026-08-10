"""
Cron cleanup temp upload — docs/ARCHITECTURE.md §7 (jalankan tiap 30 menit).

Menghapus file temp di R2 untuk upload session yang masih `pending` dan sudah
lewat `expires_at`, lalu menandai statusnya `expired`. Sengaja TIDAK memakai
Celery/Redis (AGENTS.md §10 #11, MVP sync-first) — cukup dijadwalkan lewat cron
OS / scheduler platform (mis. Railway cron) memanggil:

    python -m app.jobs.cleanup_temp_uploads
"""
import asyncio

from app.repositories.demand_history_repository import SqlDemandHistoryRepository
from app.repositories.product_repository import SqlProductRepository
from app.repositories.upload_session_repository import SqlUploadSessionRepository
from app.services.storage_service import StorageService, build_r2_client
from app.services.upload_service import UploadService
from app.db.session import get_sessionmaker


async def run() -> int:
    async with get_sessionmaker()() as session:
        # `demand`/`products` tak dipakai cleanup_expired (hanya storage+sessions),
        # tapi tetap wajib diisi — konstruktor UploadService tidak punya default.
        service = UploadService(
            storage=StorageService(build_r2_client()),
            sessions=SqlUploadSessionRepository(session),
            demand=SqlDemandHistoryRepository(session),
            products=SqlProductRepository(session),
        )
        count = await service.cleanup_expired()
        await session.commit()
        return count


def main() -> None:
    removed = asyncio.run(run())
    print(f"[cleanup_temp_uploads] {removed} temp upload session dibersihkan.")


if __name__ == "__main__":
    main()
