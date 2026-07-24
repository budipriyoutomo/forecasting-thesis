"""
DashboardService — ringkasan untuk halaman dashboard (Fase 7).

Agregasi lintas domain: jumlah material, run forecast terakhir + akurasi (MASE
rata-rata), distribusi status reorder (urgent/safe/overstock), jumlah override
terbaru. Semua dibaca lewat repository (tidak query inline di endpoint).
"""


class DashboardService:
    def __init__(self, materials, forecast_repo, reorder_repo, override_repo):
        self._materials = materials
        self._forecast = forecast_repo
        self._reorder = reorder_repo
        self._override = override_repo

    async def summary(self, user_id: str) -> dict:
        materials = await self._materials.list()
        latest_run = await self._forecast.get_latest_run_for_user(user_id)

        latest_run_summary = None
        reorder_counts = {"urgent": 0, "safe": 0, "overstock": 0}
        avg_mase = None

        if latest_run is not None:
            results = await self._forecast.list_results(str(latest_run.id))
            completed = [r for r in results if r.status == "COMPLETED"]
            mases = [float(r.mase) for r in completed if r.mase is not None]
            avg_mase = round(sum(mases) / len(mases), 4) if mases else None

            latest_run_summary = {
                "run_id": str(latest_run.id),
                "status": latest_run.status,
                "n_materials": len(results),
                "n_completed": len(completed),
                "n_failed": len(results) - len(completed),
                "avg_mase": avg_mase,
            }

            for rec in await self._reorder.list_by_run(str(latest_run.id)):
                if rec.status in reorder_counts:
                    reorder_counts[rec.status] += 1

        recent_overrides = await self._override.list_recent(limit=5)

        return {
            "n_materials": len(materials),
            "latest_run": latest_run_summary,
            "reorder_status_counts": reorder_counts,
            "n_recent_overrides": len(recent_overrides),
        }
