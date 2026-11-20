"""
Cek & normalisasi periode `demand_history` lama ke tanggal 1 (CR v3.4 §4.1).

Sejak v3.4 upload demand & import variabel eksternal menormalisasi periode ke awal bulan.
Baris yang di-upload SEBELUMNYA dengan tanggal lain (mis. 2024-01-24) tidak cocok lagi dengan
nilai variabel eksternal (tgl 1) → variabel di-drop engine. Script ini:

    python -m app.scripts.normalize_demand_periods           # laporan saja (default, aman)
    python -m app.scripts.normalize_demand_periods --apply   # geser baris yang aman ke tgl 1

Baris yang BENTROK tidak disentuh dan dilaporkan: dalam satu upload & produk, dua baris jatuh
di bulan yang sama, atau bulan itu sudah punya baris tanggal 1 (sering tanda 'Jan-24' terbaca
24-Jan tahun berjalan). Perbaiki dengan upload ulang file yang benar.
Histori tidak dihapus/digabung — hanya kolom `period` yang digeser (nilai tetap).
"""
import asyncio
import sys
from collections import Counter

from app.services.forecasting.preprocessing import normalize_period


def plan_normalization(rows, existing: set) -> tuple[list[tuple], list]:
    """→ ([(baris, periode_baru)], [baris bentrok]). `existing` = kunci baris yang sudah tgl 1."""
    def key(r):
        return str(r.upload_session_id), r.product_code, normalize_period(r.period)

    counts = Counter(key(r) for r in rows)
    fixes, conflicts = [], []
    for r in rows:
        k = key(r)
        if counts[k] > 1 or k in existing:
            conflicts.append(r)
        else:
            fixes.append((r, k[2]))
    return fixes, conflicts


async def run_normalization(repo, apply: bool = False) -> dict:
    rows = await repo.list_unnormalized()
    fixes, conflicts = plan_normalization(rows, await repo.normalized_keys()) if rows else ([], [])
    applied = 0
    if apply and fixes:
        for row, period in fixes:
            row.period = period
        await repo.flush()
        applied = len(fixes)
    return {"unnormalized": len(rows), "fixable": len(fixes), "conflicts": len(conflicts), "applied": applied}


async def main(apply: bool) -> int:
    from app.db.session import get_sessionmaker
    from app.repositories.demand_history_repository import SqlDemandHistoryRepository

    async with get_sessionmaker()() as session:
        repo = SqlDemandHistoryRepository(session)
        report = await run_normalization(repo, apply=apply)
        if apply:
            await session.commit()
    print(f"  baris bukan tgl 1   {report['unnormalized']}")
    print(f"  aman digeser        {report['fixable']}")
    print(f"  bentrok (dilewati)  {report['conflicts']}")
    print(f"  digeser             {report['applied']}" + ("" if apply else "  (laporan saja — pakai --apply)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main("--apply" in sys.argv[1:])))
