"""
Endpoint dashboard — /api/v1/dashboard (Fase 7), docs/ARCHITECTURE.md §5.

GET /dashboard/summary → ringkasan agregat (material, run terakhir, reorder, override).
"""
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_current_user, get_dashboard_service
from app.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary")
async def dashboard_summary(
    current_user: CurrentUser = Depends(get_current_user),
    service: DashboardService = Depends(get_dashboard_service),
):
    data = await service.summary(current_user.user_id)
    return {"success": True, "data": data}
