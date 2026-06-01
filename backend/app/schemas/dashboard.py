from decimal import Decimal
from pydantic import BaseModel


class SalesOverview(BaseModel):
    total_revenue: Decimal
    total_orders: int
    pending_orders: int
    completed_orders: int
    cancelled_orders: int


class InventoryOverview(BaseModel):
    total_products: int
    active_products: int
    low_stock_products: int
    out_of_stock_products: int


class TopProduct(BaseModel):
    product_id: int
    name: str
    sku: str
    total_sold: int
    revenue: Decimal


class RecentOrder(BaseModel):
    id: int
    order_number: str
    customer_name: str
    status: str
    total_amount: Decimal


class DashboardStats(BaseModel):
    sales: SalesOverview
    inventory: InventoryOverview
    top_products: list[TopProduct]
    recent_orders: list[RecentOrder]
    total_customers: int
    new_customers_this_month: int
