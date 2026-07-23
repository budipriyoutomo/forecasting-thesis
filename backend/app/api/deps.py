"""
Shared FastAPI dependencies — auth, dsb.
"""
import jwt
from fastapi import Header

from app.utils.auth import decode_access_token
from app.utils.exceptions import AuthTokenExpiredError, AuthTokenMissingOrInvalidError


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
