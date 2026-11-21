"""
User Management endpoints (CR v3.7, 21 Nov 2026) — docs/ARCHITECTURE.md §5, PRD FR-8.4.

GET  /users            → daftar user (admin)
POST /users            → daftarkan profil + role (admin); akun login dibuat di Supabase Auth
PUT  /users/{user_id}  → ubah nama / role / status aktif (admin)

RBAC: SEMUA endpoint (termasuk GET) `user.manage` = admin — daftar user berisi email pribadi,
pengecualian dari aturan "semua GET terbuka" (CR v3.5 §3.2). Logika lewat UserService.
"""
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser, get_user_service, require_permission
from app.schemas.user import UserCreate, UserOut, UserUpdate
from app.services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


def _to_response(user) -> dict:
    return UserOut(
        id=str(user.id),
        email=user.email,
        name=user.name,
        role=user.role,
        is_verified=bool(user.is_verified),
        is_active=bool(user.is_active),
        created_at=getattr(user, "created_at", None),
    ).model_dump(mode="json")


@router.get("", dependencies=[Depends(require_permission("user.manage"))])
async def list_users(service: UserService = Depends(get_user_service)):
    return {"success": True, "data": [_to_response(u) for u in await service.list()]}


@router.post("", dependencies=[Depends(require_permission("user.manage"))])
async def create_user(payload: UserCreate, service: UserService = Depends(get_user_service)):
    user = await service.create(payload)
    return JSONResponse(
        status_code=201,
        content={"success": True, "data": _to_response(user), "message": "User ditambahkan"},
    )


@router.put("/{user_id}")
async def update_user(
    user_id: str,
    payload: UserUpdate,
    actor: CurrentUser = Depends(require_permission("user.manage")),
    service: UserService = Depends(get_user_service),
):
    user = await service.update(actor.user_id, user_id, payload)
    return {"success": True, "data": _to_response(user), "message": "User diperbarui"}
