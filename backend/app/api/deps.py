"""
Shared FastAPI dependencies — auth, RBAC, service wiring.
"""
import jwt
from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.repositories.material_repository import SqlMaterialRepository
from app.repositories.user_repository import SqlUserRepository
from app.services.auth_service import AuthService
from app.services.material_service import MaterialService
from app.services.supabase_auth import SupabaseAuthenticator
from app.utils.auth import decode_access_token
from app.utils.exceptions import AuthTokenExpiredError, AuthTokenMissingOrInvalidError, ForbiddenRoleError


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
