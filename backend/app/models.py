import enum

from sqlalchemy import (
    Column, Integer, String, Text, Numeric, DateTime,
    ForeignKey, Enum, Index, CheckConstraint, func,
)
from sqlalchemy.sql import text
from sqlalchemy.orm import relationship

from app.database import Base


# ── Enums ──────────────────────────────────────────────────────────────────────

class ProductStatus(str, enum.Enum):
    ACTIVE   = "active"
    INACTIVE = "inactive"


class OrderStatus(str, enum.Enum):
    PENDING   = "pending"
    CONFIRMED = "confirmed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class TransactionType(str, enum.Enum):
    IN         = "IN"
    OUT        = "OUT"
    ADJUSTMENT = "ADJUSTMENT"


# ── Timestamp helpers ──────────────────────────────────────────────────────────
#
# created_at  → server_default=text("now()")
#               PostgreSQL sets this on INSERT; Python never touches it.
#
# updated_at  → server_default=text("now()") + onupdate=func.now()
#               SQLAlchemy injects `SET updated_at = now()` into every
#               ORM-driven UPDATE automatically.

_TS_CREATE = dict(
    type_=DateTime(timezone=True),
    nullable=False,
    server_default=text("now()"),
)

_TS_UPDATE = dict(
    type_=DateTime(timezone=True),
    nullable=False,
    server_default=text("now()"),
    onupdate=func.now(),
)


# ── Product ────────────────────────────────────────────────────────────────────

class Product(Base):
    """
    Central inventory item.

    Additional fields beyond the spec:
      description   — human-readable detail shown in UIs and reports
      category      — logical grouping; indexed for fast category-scoped queries
                      and dashboard category breakdowns
      status        — soft enable/disable; avoids deleting products that have
                      order history (referential integrity)
      created_at    — audit trail; also used for "new arrivals" queries
      updated_at    — detect stale data; useful for cache invalidation
    """

    __tablename__ = "products"
    __table_args__ = (
        # Business rule: stock can never go below zero
        CheckConstraint("stock_quantity >= 0", name="ck_products_stock_non_negative"),
        # Supports category-filtered product listings and dashboard breakdowns
        Index("ix_products_category", "category"),
        # Supports time-range inventory reports ("products added this month")
        Index("ix_products_created_at", "created_at"),
    )

    id             = Column(Integer, primary_key=True, index=True)
    name           = Column(String(200), nullable=False)
    sku            = Column(String(100), unique=True, nullable=False, index=True)
    description    = Column(Text, nullable=True)
    price          = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    category       = Column(String(100), nullable=True)
    status         = Column(
        Enum(ProductStatus, name="product_status",
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ProductStatus.ACTIVE,
        server_default=ProductStatus.ACTIVE.value,
    )
    created_at     = Column(**_TS_CREATE)
    updated_at     = Column(**_TS_UPDATE)

    # Relationships
    order_items            = relationship("OrderItem",            back_populates="product")
    inventory_transactions = relationship("InventoryTransaction", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku={self.sku!r} stock={self.stock_quantity}>"


# ── Customer ───────────────────────────────────────────────────────────────────

class Customer(Base):
    """
    Buyer of products.

    Additional fields beyond the spec:
      address     — required for shipping/delivery; also useful for regional
                    sales reporting
      created_at  — customer lifetime value starts here; used for
                    "new customers this month" dashboard stat
      updated_at  — detects profile changes; useful for sync pipelines
    """

    __tablename__ = "customers"
    __table_args__ = (
        # Supports "customers acquired this month / quarter" dashboard queries
        Index("ix_customers_created_at", "created_at"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    full_name    = Column(String(150), nullable=False)
    email        = Column(String(255), unique=True, nullable=False, index=True)
    phone_number = Column(String(20), nullable=True)
    address      = Column(Text, nullable=True)
    created_at   = Column(**_TS_CREATE)
    updated_at   = Column(**_TS_UPDATE)

    # Relationships
    orders = relationship("Order", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer id={self.id} email={self.email!r}>"


# ── Order ──────────────────────────────────────────────────────────────────────

class Order(Base):
    """
    A customer's purchase transaction.

    Additional fields beyond the spec:
      order_status  — lifecycle state machine (pending → confirmed → completed
                      or cancelled); indexed for status-filtered list views and
                      dashboard KPI counts
      updated_at    — tracks when status last changed; useful for SLA monitoring
    """

    __tablename__ = "orders"
    __table_args__ = (
        # Core filter for order management views (e.g. "show all pending")
        Index("ix_orders_order_status", "order_status"),
        # Supports date-range order reports and dashboard revenue calculations
        Index("ix_orders_created_at", "created_at"),
    )

    id           = Column(Integer, primary_key=True, index=True)
    customer_id  = Column(
        Integer,
        ForeignKey("customers.id", ondelete="RESTRICT"),  # prevent orphan orders
        nullable=False,
        index=True,
    )
    total_amount = Column(Numeric(12, 2), nullable=False, default=0)
    order_status = Column(
        Enum(OrderStatus, name="order_status",
             values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=OrderStatus.PENDING,
        server_default=OrderStatus.PENDING.value,
    )
    created_at   = Column(**_TS_CREATE)
    updated_at   = Column(**_TS_UPDATE)

    # Relationships
    customer = relationship("Customer", back_populates="orders")
    items    = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",  # removing an order removes its items
    )

    def __repr__(self) -> str:
        return f"<Order id={self.id} status={self.order_status!r} total={self.total_amount}>"


# ── OrderItem ──────────────────────────────────────────────────────────────────

class OrderItem(Base):
    """
    A single line in an order.

    Fields:
      price       — unit price *snapshot* at the moment the order was placed.
                    Decoupled from Product.price so future price changes do
                    not alter historical order values.
      line_total  — quantity × price, stored explicitly to avoid recalculation
                    on every read and to preserve correctness if price changes.
    """

    __tablename__ = "order_items"

    id         = Column(Integer, primary_key=True, index=True)
    order_id   = Column(
        Integer,
        ForeignKey("orders.id", ondelete="CASCADE"),    # cascade from Order
        nullable=False,
        index=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="RESTRICT"), # prevent deleting sold products
        nullable=False,
        index=True,
    )
    quantity   = Column(Integer, nullable=False)
    price      = Column(Numeric(10, 2), nullable=False)   # unit price at order time
    line_total = Column(Numeric(12, 2), nullable=False)   # quantity × price

    # Relationships
    order   = relationship("Order",   back_populates="items")
    product = relationship("Product", back_populates="order_items")

    def __repr__(self) -> str:
        return (
            f"<OrderItem id={self.id} "
            f"product_id={self.product_id} "
            f"qty={self.quantity} total={self.line_total}>"
        )


# ── InventoryTransaction ───────────────────────────────────────────────────────

class InventoryTransaction(Base):
    """
    Immutable ledger of every stock movement for a product.

    TransactionType:
      IN         — stock received (purchase order, return, manual restock)
      OUT        — stock consumed (sale, damage write-off)
      ADJUSTMENT — manual correction (stocktake discrepancy)

    This model is intentionally write-only from the application layer.
    A running total of stock_quantity can always be recomputed by summing
    (IN + ADJUSTMENT_positive) − (OUT + ADJUSTMENT_negative) for a product.

    No API routes are wired yet; the CRUD layer will populate this table
    as a side-effect of order creation and stock updates.
    """

    __tablename__ = "inventory_transactions"
    __table_args__ = (
        # Enables time-range stock movement queries and audit reports
        Index("ix_inventory_transactions_created_at", "created_at"),
        # Enables per-product transaction history queries
        Index("ix_inventory_transactions_product_id", "product_id"),
    )

    id               = Column(Integer, primary_key=True, index=True)
    product_id       = Column(
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    transaction_type = Column(
        Enum(TransactionType, name="transaction_type"),
        nullable=False,
    )
    quantity         = Column(Integer, nullable=False)  # always positive; direction = type
    notes            = Column(Text, nullable=True)       # optional free-text annotation
    created_at       = Column(**_TS_CREATE)

    # Relationships
    product = relationship("Product", back_populates="inventory_transactions")

    def __repr__(self) -> str:
        return (
            f"<InventoryTransaction id={self.id} "
            f"type={self.transaction_type!r} qty={self.quantity}>"
        )
