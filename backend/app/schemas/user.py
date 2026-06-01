from datetime import datetime
from pydantic import BaseModel, EmailStr, field_validator
from app.models.user import UserRole


class UserCreate(BaseModel):
    full_name: str
    email: EmailStr
    password: str
    role: UserRole = UserRole.STAFF

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        return v


class UserUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    role: UserRole | None = None
    is_active: bool | None = None


class UserRead(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    sub: str | None = None
    role: str | None = None
