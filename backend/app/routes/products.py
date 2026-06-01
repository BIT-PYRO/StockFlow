from decimal import Decimal

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ProductStatus
from app.schemas import ProductCreate, ProductUpdate, ProductResponse, RestockRequest, RestockResponse
import app.crud as crud

router = APIRouter()


@router.get("", response_model=list[ProductResponse])
def list_products(
    skip:      int = Query(0, ge=0),
    limit:     int = Query(100, ge=1, le=500),
    search:    str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Case-insensitive substring match against product name and SKU",
    ),
    category:  str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
        description="Exact category filter (case-insensitive)",
    ),
    status:    ProductStatus | None = Query(
        default=None,
        description="Filter by product status: active or inactive",
    ),
    min_price: Decimal | None = Query(
        default=None,
        ge=0,
        description="Minimum price (inclusive)",
    ),
    max_price: Decimal | None = Query(
        default=None,
        ge=0,
        description="Maximum price (inclusive)",
    ),
    db: Session = Depends(get_db),
):
    if min_price is not None and max_price is not None and min_price > max_price:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="min_price must not be greater than max_price",
        )
    return crud.get_products(
        db,
        skip=skip,
        limit=limit,
        search=search,
        category=category,
        status=status,
        min_price=min_price,
        max_price=max_price,
    )


@router.post("", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, db: Session = Depends(get_db)):
    return crud.create_product(db, payload)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, db: Session = Depends(get_db)):
    return crud.get_product(db, product_id)


@router.put("/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate, db: Session = Depends(get_db)):
    return crud.update_product(db, product_id, payload)


@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: int, db: Session = Depends(get_db)):
    crud.delete_product(db, product_id)


@router.post("/{product_id}/restock", response_model=RestockResponse, status_code=status.HTTP_200_OK)
def restock_product(product_id: int, payload: RestockRequest, db: Session = Depends(get_db)):
    """
    Manually replenish stock for a product.

    - **quantity**: units to add (must be > 0)
    - **notes**: optional annotation stored on the inventory transaction record
    """
    return crud.restock_product(db, product_id, payload)
