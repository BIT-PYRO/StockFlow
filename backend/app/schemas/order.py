from datetime import datetime
from decimal import Decimal
from pydantic import BaseModel, field_validator
from app.models.order import OrderStatus
from app.schemas.product import ProductRead
from app.schemas.customer import CustomerRead


class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int

    @field_validator("quantity")
    @classmethod
    def must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Quantity must be greater than zero")
        return v


class OrderItemRead(BaseModel):
    id: int
    product_id: int
    product: ProductRead
    quantity: int
    unit_price: Decimal
    subtotal: Decimal

    model_config = {"from_attributes": True}


class OrderCreate(BaseModel):
    customer_id: int
    items: list[OrderItemCreate]
    discount: Decimal = Decimal("0.00")
    notes: str | None = None

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: list) -> list:
        if not v:
            raise ValueError("Order must contain at least one item")
        return v


class OrderUpdate(BaseModel):
    status: OrderStatus | None = None
    discount: Decimal | None = None
    notes: str | None = None


class OrderRead(BaseModel):
    id: int
    order_number: str
    customer_id: int
    customer: CustomerRead
    status: OrderStatus
    total_amount: Decimal
    discount: Decimal
    notes: str | None
    items: list[OrderItemRead]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
