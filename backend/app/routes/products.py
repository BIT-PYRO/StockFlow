from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate, CategoryCreate, CategoryRead
from app.schemas.common import PaginatedResponse, MessageResponse
from app.services.product_service import ProductService
from app.auth.rbac import require_any_role, require_manager_or_above, require_admin
from app.models.user import User

router = APIRouter()

# ── Categories ────────────────────────────────────────────────────────────────

@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    return ProductService(db).create_category(payload)


@router.get("/categories", response_model=list[CategoryRead])
def list_categories(
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return ProductService(db).list_categories()


# ── Products ──────────────────────────────────────────────────────────────────

@router.post("", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    return ProductService(db).create(payload)


@router.get("", response_model=PaginatedResponse[ProductRead])
def list_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str = Query(None),
    category_id: int = Query(None),
    low_stock: bool = Query(False),
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return ProductService(db).list(page, page_size, search, category_id, low_stock)


@router.get("/{product_id}", response_model=ProductRead)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_role),
):
    return ProductService(db).get_by_id(product_id)


@router.patch("/{product_id}", response_model=ProductRead)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(require_manager_or_above),
):
    return ProductService(db).update(product_id, payload)


@router.delete("/{product_id}", response_model=MessageResponse)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    return ProductService(db).delete(product_id)
