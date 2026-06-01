from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.order import Order, OrderItem, OrderStatus
from app.models.product import Product
from app.models.customer import Customer
from app.schemas.dashboard import (
    DashboardStats, SalesOverview, InventoryOverview,
    TopProduct, RecentOrder,
)


class DashboardService:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_stats(self) -> DashboardStats:
        # ── Sales overview ────────────────────────────────────────────────────
        total_revenue = (
            self.db.query(func.coalesce(func.sum(Order.total_amount), 0))
            .filter(Order.status == OrderStatus.DELIVERED)
            .scalar()
        )
        total_orders = self.db.query(func.count(Order.id)).scalar()
        pending_orders = (
            self.db.query(func.count(Order.id))
            .filter(Order.status == OrderStatus.PENDING)
            .scalar()
        )
        completed_orders = (
            self.db.query(func.count(Order.id))
            .filter(Order.status == OrderStatus.DELIVERED)
            .scalar()
        )
        cancelled_orders = (
            self.db.query(func.count(Order.id))
            .filter(Order.status == OrderStatus.CANCELLED)
            .scalar()
        )

        # ── Inventory overview ────────────────────────────────────────────────
        total_products = self.db.query(func.count(Product.id)).scalar()
        active_products = (
            self.db.query(func.count(Product.id))
            .filter(Product.is_active.is_(True))
            .scalar()
        )
        low_stock = (
            self.db.query(func.count(Product.id))
            .filter(Product.stock_quantity <= Product.reorder_level, Product.stock_quantity > 0)
            .scalar()
        )
        out_of_stock = (
            self.db.query(func.count(Product.id))
            .filter(Product.stock_quantity == 0)
            .scalar()
        )

        # ── Top products by quantity sold ─────────────────────────────────────
        top_rows = (
            self.db.query(
                Product.id,
                Product.name,
                Product.sku,
                func.sum(OrderItem.quantity).label("total_sold"),
                func.sum(OrderItem.subtotal).label("revenue"),
            )
            .join(OrderItem, OrderItem.product_id == Product.id)
            .group_by(Product.id, Product.name, Product.sku)
            .order_by(func.sum(OrderItem.quantity).desc())
            .limit(5)
            .all()
        )
        top_products = [
            TopProduct(
                product_id=r.id,
                name=r.name,
                sku=r.sku,
                total_sold=r.total_sold,
                revenue=Decimal(str(r.revenue)),
            )
            for r in top_rows
        ]

        # ── Recent orders ─────────────────────────────────────────────────────
        recent_rows = (
            self.db.query(Order)
            .order_by(Order.created_at.desc())
            .limit(10)
            .all()
        )
        recent_orders = [
            RecentOrder(
                id=o.id,
                order_number=o.order_number,
                customer_name=o.customer.full_name,
                status=o.status.value,
                total_amount=o.total_amount,
            )
            for o in recent_rows
        ]

        # ── Customers ─────────────────────────────────────────────────────────
        total_customers = self.db.query(func.count(Customer.id)).scalar()
        month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_customers = (
            self.db.query(func.count(Customer.id))
            .filter(Customer.created_at >= month_start)
            .scalar()
        )

        return DashboardStats(
            sales=SalesOverview(
                total_revenue=Decimal(str(total_revenue)),
                total_orders=total_orders,
                pending_orders=pending_orders,
                completed_orders=completed_orders,
                cancelled_orders=cancelled_orders,
            ),
            inventory=InventoryOverview(
                total_products=total_products,
                active_products=active_products,
                low_stock_products=low_stock,
                out_of_stock_products=out_of_stock,
            ),
            top_products=top_products,
            recent_orders=recent_orders,
            total_customers=total_customers,
            new_customers_this_month=new_customers,
        )
