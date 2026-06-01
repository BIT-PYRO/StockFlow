from datetime import datetime, timezone
from sqlalchemy import (
    Column, Integer, String, Text, Numeric, Boolean,
    DateTime, ForeignKey,
)
from sqlalchemy.orm import relationship
from app.database import Base


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    products = relationship("Product", back_populates="category")

    def __repr__(self) -> str:
        return f"<Category id={self.id} name={self.name}>"


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, index=True)
    sku = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    price = Column(Numeric(10, 2), nullable=False)
    cost_price = Column(Numeric(10, 2), nullable=False)
    stock_quantity = Column(Integer, default=0, nullable=False)
    reorder_level = Column(Integer, default=10, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    category = relationship("Category", back_populates="products")
    order_items = relationship("OrderItem", back_populates="product")

    def __repr__(self) -> str:
        return f"<Product id={self.id} sku={self.sku} name={self.name}>"
