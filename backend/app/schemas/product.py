from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


class CategoryRead(BaseModel):
    id: int
    name: str
    description: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class ProductCreate(BaseModel):
    name: str
    sku: str
    description: str | None = None
    price: Decimal
    cost_price: Decimal
    stock_quantity: int = 0
    reorder_level: int = 10
    category_id: int | None = None

    @field_validator("price", "cost_price")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v < 0:
            raise ValueError("Price must be non-negative")
        return v

    @field_validator("stock_quantity", "reorder_level")
    @classmethod
    def must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("Quantity must be non-negative")
        return v


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    price: Decimal | None = None
    cost_price: Decimal | None = None
    stock_quantity: int | None = None
    reorder_level: int | None = None
    is_active: bool | None = None
    category_id: int | None = None


class ProductRead(BaseModel):
    id: int
    name: str
    sku: str
    description: str | None
    price: Decimal
    cost_price: Decimal
    stock_quantity: int
    reorder_level: int
    is_active: bool
    category_id: int | None
    category: CategoryRead | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
