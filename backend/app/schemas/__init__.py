from app.schemas.user import UserCreate, UserRead, UserUpdate, UserLogin
from app.schemas.product import (
    CategoryCreate, CategoryRead,
    ProductCreate, ProductRead, ProductUpdate,
)
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.schemas.order import OrderCreate, OrderRead, OrderUpdate, OrderItemCreate
from app.schemas.dashboard import DashboardStats
from app.schemas.common import PaginatedResponse, MessageResponse

__all__ = [
    "UserCreate", "UserRead", "UserUpdate", "UserLogin",
    "CategoryCreate", "CategoryRead",
    "ProductCreate", "ProductRead", "ProductUpdate",
    "CustomerCreate", "CustomerRead", "CustomerUpdate",
    "OrderCreate", "OrderRead", "OrderUpdate", "OrderItemCreate",
    "DashboardStats",
    "PaginatedResponse", "MessageResponse",
]
