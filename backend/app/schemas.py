from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models import OrderStatus, ProductStatus, TransactionType


# ── Annotated constraint aliases ───────────────────────────────────────────────
# Centralised so every schema that needs the same rule references one place.

PositiveDecimal = Annotated[Decimal, Field(gt=Decimal("0"),  decimal_places=2)]
NonNegDecimal   = Annotated[Decimal, Field(ge=Decimal("0"),  decimal_places=2)]
PositiveInt     = Annotated[int,     Field(gt=0)]
NonNegInt       = Annotated[int,     Field(ge=0)]
NonEmptyStr     = Annotated[str,     Field(min_length=1, max_length=200)]


# ── Product ────────────────────────────────────────────────────────────────────

class ProductCreate(BaseModel):
    """Payload for creating a new product."""

    name:           NonEmptyStr
    sku:            Annotated[str, Field(min_length=1, max_length=100)]
    description:    str
    price:          PositiveDecimal
    stock_quantity: NonNegInt
    category:       str
    status:         ProductStatus


class ProductUpdate(BaseModel):
    """Full update payload — all fields are required."""

    name:           NonEmptyStr
    description:    str
    price:          PositiveDecimal
    stock_quantity: NonNegInt
    category:       str
    status:         ProductStatus


class ProductResponse(BaseModel):
    """Full product representation returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id:             int
    name:           str
    sku:            str
    description:    str | None
    price:          Decimal
    stock_quantity: int
    category:       str | None
    status:         ProductStatus
    created_at:     datetime
    updated_at:     datetime


# ── Customer ───────────────────────────────────────────────────────────────────

class CustomerCreate(BaseModel):
    """Payload for registering a new customer."""

    full_name:    NonEmptyStr
    email:        EmailStr
    phone_number: str
    address:      str


class CustomerUpdate(BaseModel):
    """Full update payload for customer profiles — all fields are required."""

    full_name:    NonEmptyStr
    email:        EmailStr
    phone_number: str
    address:      str


class CustomerResponse(BaseModel):
    """Full customer representation returned from the API."""

    model_config = ConfigDict(from_attributes=True)

    id:           int
    full_name:    str
    email:        EmailStr
    phone_number: str | None
    address:      str | None
    created_at:   datetime
    updated_at:   datetime


# ── Order Item ─────────────────────────────────────────────────────────────────

class OrderItemCreate(BaseModel):
    """A single line in an order creation request."""

    product_id: PositiveInt   # must reference a valid product
    quantity:   PositiveInt   # must be >= 1; zero-quantity lines are invalid


class OrderItemResponse(BaseModel):
    """
    Full order-item representation nested inside OrderResponse.

    price      — unit price snapshot captured at order creation time.
    line_total — quantity × price, stored on the row so it is stable even
                 if the product price changes later.
    """

    model_config = ConfigDict(from_attributes=True)

    id:         int
    product_id: int
    quantity:   int
    price:      Decimal     # unit price at time of order
    line_total: Decimal     # quantity × price


# ── Order ──────────────────────────────────────────────────────────────────────

class OrderCreate(BaseModel):
    """Payload for placing a new order."""

    customer_id: PositiveInt
    items:       list[OrderItemCreate]

    @field_validator("items")
    @classmethod
    def items_not_empty(cls, v: list[OrderItemCreate]) -> list[OrderItemCreate]:
        if not v:
            raise ValueError("An order must contain at least one item")
        return v


class OrderResponse(BaseModel):
    """
    Full order representation returned from the API.

    total_amount is calculated server-side as sum(item.line_total) and
    stored on the Order row — it is never computed by the schema.
    """

    model_config = ConfigDict(from_attributes=True)

    id:           int
    customer_id:  int
    total_amount: Decimal
    order_status: OrderStatus
    created_at:   datetime
    updated_at:   datetime
    items:        list[OrderItemResponse]


# ── Order Status Update ────────────────────────────────────────────────────────

class OrderStatusUpdate(BaseModel):
    """Request body for PATCH /orders/{order_id}/status."""

    status: OrderStatus


class OrderStatusResponse(BaseModel):
    """
    Slim response returned by PATCH /orders/{order_id}/status.

    The ORM column is named order_status; validation_alias maps it to
    the 'status' key in the JSON response without touching the model.
    """

    model_config = ConfigDict(from_attributes=True)

    id:         int
    status:     OrderStatus = Field(validation_alias="order_status")
    updated_at: datetime


# ── Dashboard ──────────────────────────────────────────────────────────────────

class LowStockProduct(BaseModel):
    """A product whose stock has fallen below the low-stock threshold."""

    model_config = ConfigDict(from_attributes=True)

    id:             int
    name:           str
    sku:            str
    category:       str | None
    stock_quantity: int


class DashboardResponse(BaseModel):
    """Aggregate KPIs returned by GET /dashboard."""

    total_products:    int
    total_customers:   int
    total_orders:      int
    total_revenue:     Decimal
    pending_orders:    int
    confirmed_orders:  int
    completed_orders:  int
    cancelled_orders:  int
    low_stock_products: list[LowStockProduct]


# ── Inventory Transactions ─────────────────────────────────────────────────────

class InventoryTransactionResponse(BaseModel):
    """
    One stock-movement record returned by GET /inventory-transactions.

    previous_stock and new_stock are derived via a cumulative window function
    (sum of signed deltas ordered by created_at) — they are not stored on the
    row itself.
    """

    model_config = ConfigDict(from_attributes=True)

    transaction_id:   int
    product_id:       int
    product_name:     str
    sku:              str
    transaction_type: TransactionType
    quantity:         int
    previous_stock:   int
    new_stock:        int
    created_at:       datetime


class InventoryTransactionListResponse(BaseModel):
    """Paginated envelope for GET /inventory-transactions."""

    total:        int
    page:         int
    page_size:    int
    total_pages:  int
    transactions: list[InventoryTransactionResponse]


# ── Restock ────────────────────────────────────────────────────────────────────

class RestockRequest(BaseModel):
    """Request body for POST /products/{product_id}/restock."""

    quantity: PositiveInt
    notes:    str | None = None


class RestockResponse(BaseModel):
    """Response returned by POST /products/{product_id}/restock."""

    product_id:   int
    product_name: str
    old_stock:    int
    added_stock:  int
    new_stock:    int

