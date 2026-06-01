from datetime import datetime
from pydantic import BaseModel, EmailStr


class CustomerCreate(BaseModel):
    full_name: str
    email: EmailStr
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None


class CustomerUpdate(BaseModel):
    full_name: str | None = None
    email: EmailStr | None = None
    phone: str | None = None
    address: str | None = None
    city: str | None = None
    country: str | None = None
    is_active: bool | None = None


class CustomerRead(BaseModel):
    id: int
    full_name: str
    email: EmailStr
    phone: str | None
    address: str | None
    city: str | None
    country: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
