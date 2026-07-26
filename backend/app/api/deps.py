"""
Shared FastAPI dependencies — auth, RBAC, service wiring.
"""
import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.bom_repository import SqlBomRepository
from app.repositories.demand_history_repository import SqlDemandHistoryRepository
from app.repositories.forecast_repository import SqlForecastRepository
from app.repositories.inventory_metrics_repository import SqlInventoryMetricsRepository
from app.repositories.material_repository import SqlMaterialRepository
from app.repositories.material_requirement_repository import SqlMaterialRequirementRepository
from app.repositories.override_repository import SqlOverrideRepository
from app.repositories.product_repository import SqlProductRepository
from app.repositories.reorder_repository import SqlReorderRepository
from app.repositories.upload_session_repository import (
    SqlConsumptionHistoryRepository,
    SqlUploadSessionRepository,
)
from app.repositories.user_repository import SqlUserRepository
from app.repositories.warehouse_repository import (
    SqlWarehouseConfigRepository,
    SqlWarehouseValidationRepository,
)
from app.services.auth_service import AuthService
from app.services.bom_service import BomService
from app.services.cost_service import CostService
from app.services.dashboard_service import DashboardService
from app.services.inventory_metrics_service import InventoryMetricsService
from app.services.export_service import ExportService
from app.services.forecast_run_service import ForecastRunService
from app.services.material_service import MaterialService
from app.services.override_service import OverrideService
from app.services.product_service import ProductService
from app.services.reorder_service import ReorderService
from app.services.storage_service import StorageService, build_r2_client
from app.services.supabase_auth import SupabaseAuthenticator
from app.services.upload_service import UploadService
from app.services.warehouse_service import WarehouseService
from app.utils.auth import decode_access_token
from app.utils.exceptions import (
    AuthTokenExpiredError,
    AuthTokenMissingOrInvalidError,
    ForbiddenRoleError,
    StorageUploadFailedError,
)


class CurrentUser:
    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthTokenMissingOrInvalidError("Authorization header tidak ada atau tidak valid")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthTokenExpiredError("Token sudah kadaluarsa")
    except jwt.InvalidTokenError:
        raise AuthTokenMissingOrInvalidError("Token tidak valid")

    return CurrentUser(user_id=payload["sub"], role=payload.get("role", "ppic"))


def require_role(*roles: str):
    """RBAC dependency (FR-8.2). Contoh: `Depends(require_role("admin", "ppic"))`.

    Role user diambil dari token; kalau tidak termasuk `roles` → 403 AUTH_FORBIDDEN.
    """

    async def checker(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise ForbiddenRoleError("Role Anda tidak diizinkan mengakses resource ini.")
        return user

    return checker


def get_auth_service(session: AsyncSession = Depends(get_db)) -> AuthService:
    return AuthService(SqlUserRepository(session), SupabaseAuthenticator())


def get_material_service(session: AsyncSession = Depends(get_db)) -> MaterialService:
    return MaterialService(SqlMaterialRepository(session))


def get_product_service(session: AsyncSession = Depends(get_db)) -> ProductService:
    return ProductService(SqlProductRepository(session))


def get_bom_service(session: AsyncSession = Depends(get_db)) -> BomService:
    return BomService(
        repo=SqlBomRepository(session),
        products=SqlProductRepository(session),
        materials=SqlMaterialRepository(session),
    )


def get_upload_service(session: AsyncSession = Depends(get_db)) -> UploadService:
    return UploadService(
        storage=StorageService(build_r2_client()),
        sessions=SqlUploadSessionRepository(session),
        demand=SqlDemandHistoryRepository(session),
        products=SqlProductRepository(session),
    )


def get_forecast_run_service(session: AsyncSession = Depends(get_db)) -> ForecastRunService:
    return ForecastRunService(
        forecast_repo=SqlForecastRepository(session),
        products=SqlProductRepository(session),
        demand=SqlDemandHistoryRepository(session),
        boms=SqlBomRepository(session),
        requirements=SqlMaterialRequirementRepository(session),
    )


def get_reorder_service(session: AsyncSession = Depends(get_db)) -> ReorderService:
    return ReorderService(
        reorder_repo=SqlReorderRepository(session),
        forecast_repo=SqlForecastRepository(session),
        boms=SqlBomRepository(session),
        materials=SqlMaterialRepository(session),
    )


def get_export_service(session: AsyncSession = Depends(get_db)) -> ExportService:
    # Storage best-effort: kalau R2 belum dikonfigurasi, export tetap jalan
    # (file diunduh langsung), arsip ke R2 di-skip.
    try:
        storage = StorageService(build_r2_client())
    except StorageUploadFailedError:
        storage = None
    return ExportService(
        forecast_repo=SqlForecastRepository(session),
        reorder_repo=SqlReorderRepository(session),
        storage=storage,
    )


def get_warehouse_service(session: AsyncSession = Depends(get_db)) -> WarehouseService:
    return WarehouseService(
        config_repo=SqlWarehouseConfigRepository(session),
        validation_repo=SqlWarehouseValidationRepository(session),
        reorder_repo=SqlReorderRepository(session),
        materials=SqlMaterialRepository(session),
        forecast_repo=SqlForecastRepository(session),
    )


def get_cost_service(session: AsyncSession = Depends(get_db)) -> CostService:
    return CostService(
        forecast_repo=SqlForecastRepository(session),
        reorder_repo=SqlReorderRepository(session),
        demand_repo=SqlDemandHistoryRepository(session),
        boms=SqlBomRepository(session),
        products=SqlProductRepository(session),
    )


def get_inventory_metrics_service(session: AsyncSession = Depends(get_db)) -> InventoryMetricsService:
    return InventoryMetricsService(
        forecast_repo=SqlForecastRepository(session),
        demand_repo=SqlDemandHistoryRepository(session),
        products=SqlProductRepository(session),
        metrics_repo=SqlInventoryMetricsRepository(session),
    )


def get_dashboard_service(session: AsyncSession = Depends(get_db)) -> DashboardService:
    return DashboardService(
        materials=SqlMaterialRepository(session),
        forecast_repo=SqlForecastRepository(session),
        reorder_repo=SqlReorderRepository(session),
        override_repo=SqlOverrideRepository(session),
        warehouse_repo=SqlWarehouseValidationRepository(session),
        inventory_metrics_repo=SqlInventoryMetricsRepository(session),
    )


def get_override_service(session: AsyncSession = Depends(get_db)) -> OverrideService:
    forecast_repo = SqlForecastRepository(session)
    reorder_repo = SqlReorderRepository(session)
    requirement_repo = SqlMaterialRequirementRepository(session)
    # Resolver polimorfik: target_type → cara mengambil objek target dari DB.
    # material_requirement ditambah di Fase 8 (RECONCILIATION §Fase 8).
    resolvers = {
        "forecast_result": forecast_repo.get_result,
        "reorder_recommendation": reorder_repo.get_recommendation,
        "material_requirement": requirement_repo.get_requirement,
    }
    return OverrideService(SqlOverrideRepository(session), resolvers)
