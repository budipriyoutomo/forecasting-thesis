"""
Pydantic schemas untuk endpoint auth — docs/ARCHITECTURE.md §5, FR-8.
"""
from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    is_verified: bool


class LoginResponseData(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
