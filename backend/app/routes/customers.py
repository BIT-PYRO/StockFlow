from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.customer import CustomerCreate, CustomerRead, CustomerUpdate
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.customer_service import CustomerService
from app.auth.rbac import require_any_role, require_manager_or_above, require_admin
from app.models.user import User

router = APIRouter()


@router.post("", response_model=CustomerRead, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return CustomerService(db).create(payload)


@router.get("", response_model=PaginatedResponse[CustomerRead])
def list_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return CustomerService(db).list(page, page_size, search)


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return CustomerService(db).get_by_id(customer_id)


@router.patch("/{customer_id}", response_model=CustomerRead)
def update_customer(
    customer_id: int,
    payload: CustomerUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    return CustomerService(db).update(customer_id, payload)


@router.delete("/{customer_id}", response_model=MessageResponse)
def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return CustomerService(db).delete(customer_id)
