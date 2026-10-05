# services/api/trustguard_api/modules/auth/schemas.py
from datetime import datetime
from uuid import UUID
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from trustguard_api.modules.shared.schemas import UserRole

class RegisterRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    display_name: str = Field(..., min_length=2, max_length=120)
    password: str = Field(..., min_length=8, max_length=128)
    role: UserRole = UserRole.USER

class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: EmailStr
    password: str

class RefreshRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    refresh_token: str

class UserProfileDTO(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: str
    display_name: str
    role: UserRole
    is_active: bool
    created_at: datetime

class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"
    expires_in: int
    user: UserProfileDTO
