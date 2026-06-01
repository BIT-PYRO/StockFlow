from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.order import OrderCreate, OrderRead, OrderUpdate
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.order_service import OrderService
from app.auth.rbac import require_any_role, require_manager_or_above, require_admin
from app.models.user import User
from app.models.order import OrderStatus

router = APIRouter()


@router.post("", response_model=OrderRead, status_code=status.HTTP_201_CREATED)
def create_order(
    payload: OrderCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return OrderService(db).create(payload)


@router.get("", response_model=PaginatedResponse[OrderRead])
def list_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: OrderStatus = Query(None),
    customer_id: int = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return OrderService(db).list(page, page_size, status, customer_id)


@router.get("/{order_id}", response_model=OrderRead)
def get_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return OrderService(db).get_by_id(order_id)


@router.patch("/{order_id}", response_model=OrderRead)
def update_order(
    order_id: int,
    payload: OrderUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    return OrderService(db).update(order_id, payload)


@router.delete("/{order_id}", response_model=MessageResponse)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    return OrderService(db).cancel(order_id)
