"""
Auth endpoints (Fase 1) — docs/ARCHITECTURE.md §5, FR-8.

Semua response mengikuti envelope standar (AGENTS.md §4). Seleksi kredensial &
penerbitan token lewat AuthService (app/services/auth_service.py), tidak inline.
"""
from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, get_auth_service, get_current_user
from app.schemas.auth import LoginRequest, LoginResponseData, UserResponse
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_response(user) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_verified=user.is_verified,
    )


@router.post("/login")
async def login(payload: LoginRequest, service: AuthService = Depends(get_auth_service)):
    token, user = await service.login(payload.email, payload.password)
    data = LoginResponseData(access_token=token, user=_user_response(user))
    return {"success": True, "data": data.model_dump()}


@router.get("/me")
async def me(
    current: CurrentUser = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
):
    user = await service.get_profile(current.user_id)
    return {"success": True, "data": _user_response(user).model_dump()}
