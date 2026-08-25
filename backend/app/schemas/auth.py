"""Auth-related Pydantic schemas."""

import uuid
from pydantic import BaseModel, EmailStr

from app.models.user import Role
from app.schemas.common import ORMBase


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(ORMBase):
    id: uuid.UUID
    email: str
    full_name: str
    role: Role
    is_active: bool


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
